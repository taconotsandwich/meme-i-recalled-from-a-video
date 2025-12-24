"""OCR module for text extraction from video frames."""
import cv2
import re
import warnings
import Levenshtein
import numpy as np
from opencc import OpenCC

# Suppress Torch pin_memory warning on MPS (M1/M2/M3/M4 Macs)
warnings.filterwarnings("ignore", message=".*pin_memory.*device pinned memory won't be used.*")

# Global variable for EasyOCR reader (lazy loading)
reader_easyocr = None

def get_easyocr_langs(lang_string):
    """Map standard language codes to EasyOCR codes."""
    mapping = {
        'eng': 'en', 'en': 'en',
        'chi_tra': 'ch_tra', 'chi_sim': 'ch_sim', 'zh': 'ch_sim',
        'chi_sim_to_tra': 'ch_sim',
        'jpn': 'ja', 'ja': 'ja',
        'kor': 'ko', 'ko': 'ko',
        'fra': 'fr', 'fr': 'fr',
        'deu': 'de', 'de': 'de',
        'spa': 'es', 'es': 'es',
        'ita': 'it', 'it': 'it',
    }
    parts = lang_string.split('+')
    return [mapping.get(l, l) for l in parts]

def get_reader(lang='eng'):
    global reader_easyocr
    if reader_easyocr is None:
        import easyocr
        easy_langs = get_easyocr_langs(lang)
        reader_easyocr = easyocr.Reader(easy_langs, gpu=True)
    return reader_easyocr

def extract_full_ocr_results(frame, lang='eng'):
    """Extract all text with bounding boxes from a frame."""
    reader = get_reader(lang)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return reader.readtext(rgb)

def calculate_region_from_coords(y_coords, h):
    """Calculate the best y-range from collected y-coordinates."""
    if not y_coords:
        return (int(h * 0.66), h)

    bins = np.zeros(h)
    for y_min, y_max in y_coords:
        bins[int(max(0, y_min)):int(min(h, y_max))] += 1

    max_freq = np.max(bins)
    if max_freq == 0:
        return (int(h * 0.66), h)
        
    threshold = max_freq * 0.5
    active_indices = np.where(bins >= threshold)[0]
    
    if len(active_indices) == 0:
        return (int(h * 0.66), h)

    y_start = int(max(0, np.min(active_indices) - 10))
    y_end = int(min(h, np.max(active_indices) + 10))
    
    if (y_end - y_start) < h * 0.05 or (y_end - y_start) > h * 0.8:
        return (int(h * 0.66), h)

    return (y_start, y_end)

def filter_ocr_results_by_region(results, region, lang='eng'):
    """Filter OCR results to only include text within the specified y-region."""
    if region == 'all':
        text = ' '.join([r[1] for r in results]).strip()
    else:
        y_start, y_end = region
        filtered_text = []
        for (bbox, text_block, prob) in results:
            if prob > 0.3:
                y_min = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                y_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                # Check if the text block overlaps significantly with our target region
                overlap_y_start = max(y_start, y_min)
                overlap_y_end = min(y_end, y_max)
                if overlap_y_end > overlap_y_start:
                    overlap_height = overlap_y_end - overlap_y_start
                    text_height = y_max - y_min
                    if text_height > 0 and (overlap_height / text_height) > 0.5:
                        filtered_text.append(text_block)
        text = ' '.join(filtered_text).strip()
    
    # Handle Simplified to Traditional translation if requested
    if lang == 'chi_sim_to_tra' and text:
        converter = OpenCC('s2t')
        text = converter.convert(text)
        
    return text

def normalize_text(text):
    if not text or len(text.strip()) < 2:
        return ''
    normalized = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text).strip().lower()
    return ' '.join(normalized.split())

def is_text_significantly_different(a, b, threshold=0.85):
    if not a and not b: return False
    if not a or not b: return True
    return Levenshtein.ratio(a, b) < threshold

def has_meaningful_text(text):
    if not text: return False
    normalized = normalize_text(text)
    return len(normalized) >= 2