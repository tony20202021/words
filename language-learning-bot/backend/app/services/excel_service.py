"""
Service for Excel file processing and export.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import io
import json

import pandas as pd
from datetime import datetime

from app.services.word_service import WordService
from app.api.models.word import WordCreate, WordUpdate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExcelService:
    """Service for handling Excel file operations and data export."""
    
    def __init__(self, word_service: WordService):
        """
        Initialize the Excel service.
        
        Args:
            word_service: Word service instance
        """
        self.word_service = word_service
    
    async def process_excel_file(
        self,
        contents: bytes,
        language_id: str,
        column_word: int,
        column_translation: int,
        column_transcription: int,
        column_number: Optional[int] = None,
        start_row: int = 0
    ) -> Dict[str, Any]:
        """
        Process Excel file with words.
        
        Args:
            contents: Binary content of the Excel file
            language_id: ID of the language
            column_word: Column index for foreign words (0-based)
            column_translation: Column index for translations (0-based)
            column_transcription: Column index for transcriptions (0-based)
            column_number: Optional column index for word numbers (0-based)
            start_row: Row index to start processing from (0-based): 0 if no headers, 1 if headers
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing Excel file for language ID: {language_id}")
        
        result = {
            "total_processed": 0,
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            # Read Excel file into DataFrame
            df = pd.read_excel(io.BytesIO(contents), header=None, skiprows=start_row)
            
            # Get total number of rows
            total_rows = len(df)
            result["total_processed"] = total_rows
            
            logger.info(f"Found {total_rows} rows in Excel file (skipping first {start_row} rows)")
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Skip rows with missing required values
                    if pd.isna(row[column_word]) or pd.isna(row[column_translation]):
                        logger.warning(f"Skipping row {index+1} due to missing required values")
                        result["skipped"] += 1
                        continue
                    
                    # Extract values from row
                    word_foreign = str(row[column_word]).strip()
                    translation = str(row[column_translation]).strip()
                    
                    # Handle optional values
                    transcription = str(row[column_transcription]).strip() if not pd.isna(row[column_transcription]) else None
                    
                    # Get word number from column or use index+1
                    if column_number is not None and not pd.isna(row[column_number]):
                        word_number = int(row[column_number])
                    else:
                        word_number = index + 1
                    
                    # Create word data using Pydantic model
                    word_data = WordCreate(
                        language_id=language_id,
                        word_foreign=word_foreign,
                        translation=translation,
                        transcription=transcription,
                        word_number=word_number
                    )
                    
                    # Check if word already exists by language_id and word_number
                    existing_word = await self.word_service.get_word_by_number(language_id, word_number)
                    
                    if existing_word:
                        # Update existing word
                        word_id = existing_word.id
                        
                        # Create update model with only the fields we want to update
                        update_data = WordUpdate(
                            word_foreign=word_foreign,
                            translation=translation,
                            transcription=transcription
                        )
                        
                        await self.word_service.update_word(word_id, update_data.dict(exclude_unset=True))
                        result["updated"] += 1
                    else:
                        # Create new word
                        await self.word_service.create_word(word_data.dict())
                        result["added"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {index+1}: {str(e)}", exc_info=True)
                    result["errors"].append(f"Row {index+1}: {str(e)}")
                    result["skipped"] += 1
            
            logger.info(f"Excel processing complete: {result['added']} added, {result['updated']} updated, {result['skipped']} skipped")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
            result["errors"].append(f"File processing error: {str(e)}")
            return result
    
    def _clean_text_for_export(self, text: str) -> str:
        """
        Clean text for export by removing/replacing problematic characters.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ""
        
        # Replace line breaks with spaces
        cleaned = text.replace('\n', '.').replace('\r', '.')
        
        # Replace multiple spaces with single space
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Strip leading/trailing whitespace
        return cleaned.strip()
    
    def export_words_to_excel(
        self,
        words: List[Dict[str, Any]],
        language_name: str,
        start_word: Optional[int] = None,
        end_word: Optional[int] = None
    ) -> Tuple[io.BytesIO, str]:
        """
        Export words to Excel format.
        
        Args:
            words: List of word dictionaries
            language_name: Name of the language
            start_word: Optional start word number
            end_word: Optional end word number
            
        Returns:
            Tuple of (BytesIO buffer, filename)
        """
        logger.info(f"Exporting {len(words)} words to Excel for language '{language_name}'")
        
        # Prepare export data
        export_data = []
        for word in words:
            word_data = {
                "№": word.get("word_number", ""),
                "Слово": self._clean_text_for_export(word.get("word_foreign", "")),
                "Перевод": self._clean_text_for_export(word.get("translation", "")),
                "Транскрипция": self._clean_text_for_export(word.get("transcription", ""))
            }
            export_data.append(word_data)
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create ASCII-safe language name for filename
        language_name_ascii = "".join(c for c in language_name if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
        if not language_name_ascii:
            language_name_ascii = "language"  # fallback name
        
        range_suffix = ""
        if start_word is not None or end_word is not None:
            range_suffix = f"_{start_word or 1}-{end_word or 'end'}"
        
        filename = f"words_{language_name_ascii}{range_suffix}_{timestamp}.xlsx"
        
        # Create Excel file in memory
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Words')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Words']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        logger.info(f"Excel file created: {filename}")
        return output, filename
    
    def export_words_to_csv(
        self,
        words: List[Dict[str, Any]],
        language_name: str,
        start_word: Optional[int] = None,
        end_word: Optional[int] = None
    ) -> Tuple[io.BytesIO, str]:
        """
        Export words to CSV format.
        
        Args:
            words: List of word dictionaries
            language_name: Name of the language
            start_word: Optional start word number
            end_word: Optional end word number
            
        Returns:
            Tuple of (BytesIO buffer, filename)
        """
        logger.info(f"Exporting {len(words)} words to CSV for language '{language_name}'")
        
        # Prepare export data
        export_data = []
        for word in words:
            word_data = {
                "№": word.get("word_number", ""),
                "Слово": self._clean_text_for_export(word.get("word_foreign", "")),
                "Перевод": self._clean_text_for_export(word.get("translation", "")),
                "Транскрипция": self._clean_text_for_export(word.get("transcription", ""))
            }
            export_data.append(word_data)
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create ASCII-safe language name for filename
        language_name_ascii = "".join(c for c in language_name if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
        if not language_name_ascii:
            language_name_ascii = "language"  # fallback name
        
        range_suffix = ""
        if start_word is not None or end_word is not None:
            range_suffix = f"_{start_word or 1}-{end_word or 'end'}"
        
        filename = f"words_{language_name_ascii}{range_suffix}_{timestamp}.csv"
        
        # Create CSV file in memory
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        # Convert to bytes with BOM for Excel compatibility
        csv_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
        
        logger.info(f"CSV file created: {filename}")
        return csv_bytes, filename
    
    def export_words_to_json(
        self,
        words: List[Dict[str, Any]],
        language_info: Dict[str, str],
        start_word: Optional[int] = None,
        end_word: Optional[int] = None
    ) -> Tuple[io.BytesIO, str]:
        """
        Export words to JSON format.
        
        Args:
            words: List of word dictionaries
            language_info: Dictionary with language information (id, name_ru, name_foreign)
            start_word: Optional start word number
            end_word: Optional end word number
            
        Returns:
            Tuple of (BytesIO buffer, filename)
        """
        logger.info(f"Exporting {len(words)} words to JSON for language '{language_info.get('name_ru')}'")
        
        # Prepare export data
        export_words = []
        for word in words:
            word_data = {
                "word_number": word.get("word_number", ""),
                "word_foreign": self._clean_text_for_export(word.get("word_foreign", "")),
                "translation": self._clean_text_for_export(word.get("translation", "")),
                "transcription": self._clean_text_for_export(word.get("transcription", ""))
            }
            export_words.append(word_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create ASCII-safe language name for filename
        language_name_ascii = "".join(c for c in language_info.get('name_ru', '') if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
        if not language_name_ascii:
            language_name_ascii = "language"  # fallback name
        
        range_suffix = ""
        if start_word is not None or end_word is not None:
            range_suffix = f"_{start_word or 1}-{end_word or 'end'}"
        
        filename = f"words_{language_name_ascii}{range_suffix}_{timestamp}.json"
        
        # Create JSON structure
        json_data = {
            "language": {
                "id": language_info.get("id"),
                "name_ru": language_info.get("name_ru"),
                "name_foreign": language_info.get("name_foreign")
            },
            "export_info": {
                "timestamp": timestamp,
                "total_words": len(export_words),
                "word_range": {
                    "start": start_word,
                    "end": end_word
                } if start_word or end_word else None
            },
            "words": export_words
        }
        
        # Create JSON file in memory
        output = io.BytesIO(json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'))
        
        logger.info(f"JSON file created: {filename}")
        return output, filename
