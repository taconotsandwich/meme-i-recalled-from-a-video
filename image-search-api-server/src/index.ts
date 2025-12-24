import { Hono } from 'hono';
import { InteractionType, InteractionResponseType, verifyKey } from 'discord-interactions';
import { findImagesBySubtitle, findImageBySerialNumber, Env } from './services/imageSearch';

// Define the environment variables we expect
type Bindings = {
  DB: D1Database;
  IMAGES: R2Bucket;
  DISCORD_PUBLIC_KEY: string;
  DISCORD_APP_ID: string;
  DISCORD_BOT_TOKEN: string;
  ADMIN_SECRET: string;
};

const app = new Hono<{ Bindings: Bindings }>();

// 1. Image Proxy Endpoint (Serve R2 images via Worker)
app.get('/img/*', async (c) => {
  const path = c.req.path.replace('/img/', '');
  const object = await c.env.IMAGES.get(path);

  if (!object) {
    return c.text('Image not found', 404);
  }

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);

  return new Response(object.body, {
    headers,
  });
});

// 2. Interactions Endpoint (Webhook)
app.get('/api/discord/webhook', (c) => c.text('Discord Webhook is active! (Use POST for actual interactions)'));

app.post('/api/discord/webhook', async (c) => {
  const signature = c.req.header('X-Signature-Ed25519');
  const timestamp = c.req.header('X-Signature-Timestamp');
  const body = await c.req.text();

  if (!signature || !timestamp || !c.env.DISCORD_PUBLIC_KEY) {
    console.error('Missing verification headers or DISCORD_PUBLIC_KEY');
    return c.text('Missing signature, timestamp, or public key', 401);
  }

  const isValidRequest = verifyKey(body, signature, timestamp, c.env.DISCORD_PUBLIC_KEY);
  if (!isValidRequest) {
    console.error('Invalid request signature. Check if DISCORD_PUBLIC_KEY is correct.');
    return c.text('Invalid request signature', 401);
  }

  const interaction = JSON.parse(body);

  // Handle Ping
  if (interaction.type === InteractionType.PING) {
    return c.json({ type: InteractionResponseType.PONG });
  }

  // Handle Slash Commands
  if (interaction.type === InteractionType.APPLICATION_COMMAND) {
    const { name, options } = interaction.data;
    const interactionToken = interaction.token;
    const appId = c.env.DISCORD_APP_ID;

    // We use c.executionCtx.waitUntil to perform the search AFTER responding to Discord
    c.executionCtx.waitUntil((async () => {
      try {
        let responseContent: any = { content: 'Something went wrong' };

        if (name === 'search') {
          const query = options?.find((o: any) => o.name === 'query')?.value;
          if (!query) {
            responseContent = { content: 'Please provide a search query.' };
          } else {
            const images = await findImagesBySubtitle(c.env.DB, query);
            if (images.length === 0) {
              responseContent = { content: `No images found for "${query}"` };
            } else if (images.length === 1) {
              const fullImageUrl = new URL(`/img/${images[0].image_url}`, c.req.url).toString();
              responseContent = { 
                content: `Found: ${images[0].subtitle}`, 
                embeds: [{ image: { url: fullImageUrl } }] 
              };
            } else {
              const list = images.map(img => `- ${img.subtitle} (ID: ${img.id})`).join('\n');
              responseContent = { content: `Multiple found for "${query}". Use /serial to pick one:\n${list}` };
            }
          }
        }

        if (name === 'serial') {
          const id = options?.find((o: any) => o.name === 'id')?.value;
          const image = await findImageBySerialNumber(c.env.DB, id);
          if (image) {
            const fullImageUrl = new URL(`/img/${image.image_url}`, c.req.url).toString();
            responseContent = { 
              content: `ID: ${image.id} - ${image.subtitle}`, 
              embeds: [{ image: { url: fullImageUrl } }] 
            };
          } else {
            responseContent = { content: `No image found with ID ${id}` };
          }
        }

        // Send the actual result back to Discord using the interaction token
        await fetch(`https://discord.com/api/v10/webhooks/${appId}/${interactionToken}/messages/@original`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(responseContent)
        });

      } catch (error) {
        console.error(error);
        await fetch(`https://discord.com/api/v10/webhooks/${appId}/${interactionToken}/messages/@original`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: 'Internal server error while searching.' })
        });
      }
    })());

    // Immediately respond to Discord so it doesn't timeout
    return c.json({
      type: InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
    });
  }

  return c.json({ error: 'Unknown interaction' }, 400);
});

// 3. Command Registration Helper (Run this once via browser/curl)
app.get('/register-commands', async (c) => {
  const secret = c.req.query('secret');
  if (!c.env.ADMIN_SECRET || secret !== c.env.ADMIN_SECRET) {
    return c.text('Unauthorized', 401);
  }

  if (!c.env.DISCORD_APP_ID || !c.env.DISCORD_BOT_TOKEN) {
    return c.text('Missing Discord App ID or Bot Token', 500);
  }

  const commands = [
    {
      name: 'search',
      description: 'Search for a meme image by subtitle',
      options: [{
        name: 'query',
        description: 'The subtitle text to search for',
        type: 3, // STRING
        required: true
      }]
    },
    {
      name: 'serial',
      description: 'Get a meme image by its specific ID',
      options: [{
        name: 'id',
        description: 'The numeric ID of the image',
        type: 4, // INTEGER
        required: true
      }]
    }
  ];

  const response = await fetch(`https://discord.com/api/v10/applications/${c.env.DISCORD_APP_ID}/commands`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bot ${c.env.DISCORD_BOT_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(commands)
  });

  if (response.ok) {
    return c.text('Commands registered successfully!');
  } else {
    const errorText = await response.text();
    return c.text(`Failed to register commands: ${errorText}`, 500);
  }
});

app.get('/', (c) => c.text('Meme Search Bot is Alive!'));

export default app;
