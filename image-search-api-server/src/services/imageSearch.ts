// Define the shape of our Environment to include the D1 binding
export interface Env {
  DB: D1Database;
}

export interface Image {
  id: number;
  subtitle: string;
  image_url: string;
}

export async function findImagesBySubtitle(db: D1Database, subtitle: string): Promise<Image[]> {
  try {
    const query = `SELECT id, subtitle, filepath as image_url FROM video_frames WHERE LOWER(subtitle) LIKE ? LIMIT 5`;
    const { results } = await db.prepare(query)
      .bind(`%${subtitle.toLowerCase()}%`)
      .all<Image>();
    
    return results || [];
  } catch (error) {
    console.error('Error finding images by subtitle:', error);
    throw error;
  }
}

export async function findImageBySerialNumber(db: D1Database, serialNumber: number): Promise<Image | null> {
  try {
    const query = `SELECT id, subtitle, filepath as image_url FROM video_frames WHERE id = ?`;
    const result = await db.prepare(query)
      .bind(serialNumber)
      .first<Image>();
    
    return result;
  } catch (error) {
    console.error('Error finding image by serial number:', error);
    throw error;
  }
}