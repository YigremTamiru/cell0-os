#!/usr/bin/env python3
"""Extract Apple Notes from NoteStore.sqlite and convert to Markdown.

Apple Notes uses gzip-compressed protobuf format for note content.
"""

import sqlite3
import os
import re
import gzip
import struct
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime

DB_PATH = os.path.expanduser("~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite")
OUTPUT_DIR = os.path.expanduser("~/.openclaw/workspace/notes_export")

class HTMLStripper(HTMLParser):
    """Simple HTML to text converter."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
        self.convert_charrefs = True
    
    def handle_data(self, d):
        self.fed.append(d)
    
    def handle_starttag(self, tag, attrs):
        if tag in ['p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.fed.append('\n')
    
    def handle_endtag(self, tag):
        if tag in ['p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.fed.append('\n')
    
    def get_text(self):
        return ''.join(self.fed)

def strip_html(html):
    """Convert HTML to plain text."""
    s = HTMLStripper()
    try:
        s.feed(html)
        text = s.get_text()
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text
    except:
        return html

def sanitize_filename(title):
    """Convert title to safe filename."""
    if not title:
        return "untitled"
    # Remove or replace unsafe characters
    title = re.sub(r'[<>:"/\\|?*]', '_', title)
    title = re.sub(r'\s+', '_', title)
    title = title.strip('._')
    # Limit length
    if len(title) > 100:
        title = title[:100]
    return title if title else "untitled"

def extract_text_from_note_data(data):
    """Extract text from Apple Notes binary format.
    
    The data is typically gzip compressed protobuf.
    """
    if not data:
        return ""
    
    # Check if gzip compressed (magic number 1f 8b)
    if data[:2] == b'\x1f\x8b':
        try:
            decompressed = gzip.decompress(data)
            data = decompressed
        except Exception as e:
            pass
    
    # Try to extract text from the decompressed data
    # Apple Notes uses a mix of formats
    
    # Method 1: Look for UTF-8 text
    text = extract_utf8_text(data)
    if text:
        return text
    
    # Method 2: Look for UTF-16 text
    text = extract_utf16_text(data)
    if text:
        return text
    
    # Method 3: Extract readable strings
    return extract_readable_strings(data)

def extract_utf8_text(data):
    """Try to extract UTF-8 encoded text."""
    try:
        # Decode with error handling
        text = data.decode('utf-8', errors='ignore')
        
        # Look for HTML content
        if any(tag in text.lower() for tag in ['<html', '<body', '<p>', '<div', '<span', '<br', '<h1', '<h2']):
            return strip_html(text)
        
        # Look for reasonable text content
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            # Keep lines that have actual readable content
            if len(line) > 1 and any(c.isalpha() for c in line):
                # Filter out lines that are mostly special chars
                alpha_ratio = sum(1 for c in line if c.isalpha() or c.isspace()) / len(line) if line else 0
                if alpha_ratio > 0.5:
                    lines.append(line)
        
        if lines:
            return '\n'.join(lines)
    except:
        pass
    return ""

def extract_utf16_text(data):
    """Try to extract UTF-16 encoded text."""
    for encoding in ['utf-16-le', 'utf-16-be']:
        try:
            text = data.decode(encoding, errors='ignore')
            # Look for reasonable content
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if len(line) > 1 and any(c.isalpha() for c in line):
                    lines.append(line)
            if lines and sum(len(l) for l in lines) > 20:
                return '\n'.join(lines)
        except:
            pass
    return ""

def extract_readable_strings(data):
    """Extract readable ASCII/UTF-8 strings from binary data."""
    # Find sequences of printable characters
    pattern = rb'[\x20-\x7E\x80-\xFF]{3,}'
    matches = re.findall(pattern, data)
    
    decoded = []
    for m in matches:
        try:
            text = m.decode('utf-8', errors='ignore')
            # Filter for actual words/sentences
            if re.search(r'[a-zA-Z]{2,}', text):
                decoded.append(text)
        except:
            pass
    
    # Join with newlines and clean up
    result = '\n'.join(decoded)
    # Remove very short lines that are likely garbage
    lines = [l for l in result.split('\n') if len(l.strip()) > 2]
    return '\n'.join(lines[:200])  # Limit to first 200 matches

def get_folder_for_note(cursor, folder_id):
    """Get folder name for a note."""
    if not folder_id:
        return None
    cursor.execute("SELECT ZTITLE FROM ZICCLOUDSYNCINGOBJECT WHERE Z_PK = ? AND Z_ENT = 14", (folder_id,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else None

def should_skip_folder(folder_name):
    """Check if folder should be skipped."""
    if not folder_name:
        return False
    skip_patterns = ['the only', 'theone', 'the_one']
    folder_lower = folder_name.lower()
    return any(pattern in folder_lower for pattern in skip_patterns)

def is_attachment_note(title):
    """Check if note appears to be an attachment."""
    if not title:
        return False
    attachment_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip', 
                            '.html', '.docx', '.pptx', '.mov', '.mp4', '.heic']
    return any(title.lower().endswith(ext) for ext in attachment_extensions)

def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all notes (Z_ENT = 4) with their folder info
    cursor.execute("""
        SELECT n.Z_PK, n.ZTITLE, n.ZFOLDER, d.ZDATA, n.ZCREATIONDATE, n.ZMODIFICATIONDATE
        FROM ZICCLOUDSYNCINGOBJECT n
        LEFT JOIN ZICNOTEDATA d ON n.ZNOTEDATA = d.Z_PK
        WHERE n.Z_ENT = 4
        ORDER BY n.ZMODIFICATIONDATE DESC
    """)
    
    notes = cursor.fetchall()
    exported_count = 0
    skipped_count = 0
    empty_count = 0
    
    # Track used filenames to avoid collisions
    used_names = set()
    
    for note_id, title, folder_id, data, creation_date, mod_date in notes:
        # Get folder name and check if we should skip
        folder_name = get_folder_for_note(cursor, folder_id)
        if should_skip_folder(folder_name):
            skipped_count += 1
            continue
        
        # Extract text content
        content = extract_text_from_note_data(data) if data else ""
        content = content.strip()
        
        # Determine filename
        base_name = sanitize_filename(title)
        filename = base_name
        counter = 1
        while filename in used_names:
            filename = f"{base_name}_{counter}"
            counter += 1
        used_names.add(filename)
        
        # Build markdown content
        md_content = f"""---
note_id: {note_id}
"""
        if title:
            md_content += f"title: {title}\n"
        if folder_name:
            md_content += f"folder: {folder_name}\n"
        md_content += "---\n\n"
        
        if content and len(content) > 5:
            md_content += content
        elif is_attachment_note(title):
            md_content += f"*(Attachment: {title})*"
        else:
            md_content += "*(Empty note)*"
            empty_count += 1
        
        md_content += "\n"
        
        # Write file
        filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            exported_count += 1
        except Exception as e:
            print(f"Error writing {filename}: {e}")
        
        if exported_count % 50 == 0:
            print(f"Exported {exported_count} notes...")
    
    conn.close()
    
    print(f"\n✅ Export Complete!")
    print(f"Exported: {exported_count} notes")
    print(f"Empty notes: {empty_count}")
    print(f"Skipped (folder filter): {skipped_count}")
    print(f"Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
