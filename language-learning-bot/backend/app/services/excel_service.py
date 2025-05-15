"""
Service for Excel file processing.
"""

import logging
from typing import Dict, Any, Optional, List
import io

import pandas as pd

from app.services.word_service import WordService
from app.api.models.word import WordCreate, WordUpdate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExcelService:
    """Service for handling Excel file operations."""
    
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