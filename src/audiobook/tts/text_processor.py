"""
Text processing utilities for the audiobook TTS system.
"""
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..config import TextPreset, MAX_WORDS_PER_CHUNK

@dataclass
class TextChunk:
    """Represents a chunk of text to be processed."""
    text: str
    start_index: int
    end_index: int
    chunk_number: int
    is_complete_sentence: bool = True
    metadata: Optional[dict] = None

class TextProcessor:
    """Handles text processing and chunking for TTS generation."""
    
    def __init__(self, preset: TextPreset = TextPreset.AUDIOBOOK):
        self.preset = preset
        self.sentence_end_pattern = re.compile(r'[.!?]+[\s"\')\]]*(\\n)?')
        self.word_pattern = re.compile(r'\b\w+\b')
        self.whitespace_pattern = re.compile(r'\s+')
        
        # Pause durations in seconds
        self._pause_settings = {
            TextPreset.AUDIOBOOK: {
                'paragraph_pause': 1.0,
                'end_sentence_pause': 0.5,
                'punctuation_pause': 0.2,
            },
            TextPreset.DIALOGUE: {
                'paragraph_pause': 1.5,
                'end_sentence_pause': 0.7,
                'punctuation_pause': 0.3,
            },
            TextPreset.NARRATION: {
                'paragraph_pause': 0.8,
                'end_sentence_pause': 0.4,
                'punctuation_pause': 0.15,
            }
        }
        
        # Set pause attributes based on preset
        preset_pauses = self._pause_settings[preset]
        self.paragraph_pause = preset_pauses['paragraph_pause']
        self.end_sentence_pause = preset_pauses['end_sentence_pause']
        self.punctuation_pause = preset_pauses['punctuation_pause']
    
    def count_words(self, text: str) -> int:
        """Count the number of words in a text string."""
        return len(self.word_pattern.findall(text))
    
    def is_sentence_end(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation."""
        return bool(self.sentence_end_pattern.search(text))
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        return self.whitespace_pattern.sub(' ', text).strip()
    
    def find_sentence_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """Find the start and end indices of sentences in text."""
        boundaries = []
        start = 0
        
        for match in self.sentence_end_pattern.finditer(text):
            end = match.end()
            boundaries.append((start, end))
            start = end
            
        # Add any remaining text as a final boundary
        if start < len(text):
            boundaries.append((start, len(text)))
            
        return boundaries
    
    def chunk_text(self, text: str, max_words: int = MAX_WORDS_PER_CHUNK) -> List[TextChunk]:
        """Split text into chunks of approximately max_words words."""
        text = self.normalize_whitespace(text)
        chunks = []
        chunk_number = 0
        
        # Get sentence boundaries
        boundaries = self.find_sentence_boundaries(text)
        current_chunk = []
        current_word_count = 0
        chunk_start = 0
        
        for start, end in boundaries:
            sentence = text[start:end].strip()
            sentence_word_count = self.count_words(sentence)
            
            # If adding this sentence would exceed max_words
            if current_word_count + sentence_word_count > max_words and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = ' '.join(current_chunk)
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_index=chunk_start,
                    end_index=start,
                    chunk_number=chunk_number,
                    is_complete_sentence=True
                ))
                chunk_number += 1
                current_chunk = []
                current_word_count = 0
                chunk_start = start
            
            # If single sentence is longer than max_words, split it
            if sentence_word_count > max_words:
                words = sentence.split()
                temp_chunk = []
                temp_word_count = 0
                word_start = start
                
                for word in words:
                    if temp_word_count + 1 > max_words:
                        # Create chunk from accumulated words
                        chunk_text = ' '.join(temp_chunk)
                        chunks.append(TextChunk(
                            text=chunk_text,
                            start_index=word_start,
                            end_index=start + len(' '.join(temp_chunk)),
                            chunk_number=chunk_number,
                            is_complete_sentence=False
                        ))
                        chunk_number += 1
                        temp_chunk = []
                        temp_word_count = 0
                        word_start = start + len(' '.join(temp_chunk))
                    
                    temp_chunk.append(word)
                    temp_word_count += 1
                
                # Add any remaining words
                if temp_chunk:
                    chunk_text = ' '.join(temp_chunk)
                    chunks.append(TextChunk(
                        text=chunk_text,
                        start_index=word_start,
                        end_index=end,
                        chunk_number=chunk_number,
                        is_complete_sentence=self.is_sentence_end(chunk_text)
                    ))
                    chunk_number += 1
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_word_count
        
        # Add any remaining text as final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(TextChunk(
                text=chunk_text,
                start_index=chunk_start,
                end_index=len(text),
                chunk_number=chunk_number,
                is_complete_sentence=self.is_sentence_end(chunk_text)
            ))
        
        return chunks
    
    def estimate_pause_duration(self, chunk: TextChunk, next_chunk: Optional[TextChunk] = None) -> float:
        """Estimate the appropriate pause duration after a chunk."""
        if not next_chunk:  # End of text
            return self.paragraph_pause
            
        if not chunk.is_complete_sentence:
            return self.punctuation_pause
            
        # Check if chunks are from different paragraphs
        if "\\n" in chunk.text[-5:] or "\\n" in next_chunk.text[:5]:
            return self.paragraph_pause
            
        return self.end_sentence_pause
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for TTS processing."""
        # Replace common abbreviations
        text = re.sub(r'Mr\.', 'Mister', text)
        text = re.sub(r'Mrs\.', 'Misses', text)
        text = re.sub(r'Dr\.', 'Doctor', text)
        text = re.sub(r'Prof\.', 'Professor', text)
        text = re.sub(r'Sr\.', 'Senior', text)
        text = re.sub(r'Jr\.', 'Junior', text)
        
        # Normalize numbers
        text = re.sub(r'\d+', lambda m: self._number_to_words(m.group()), text)
        
        # Normalize whitespace
        text = self.normalize_whitespace(text)
        
        return text
    
    def _number_to_words(self, number_str: str) -> str:
        """Convert a number string to words."""
        # This is a simplified version - you might want to use a library like num2words
        try:
            num = int(number_str)
            if num < 0:
                return f"negative {self._number_to_words(str(abs(num)))}"
            elif num == 0:
                return "zero"
            elif num <= 999999:
                return str(num)  # Keep numbers as digits for now
            else:
                return f"{num:,}"  # Add commas for large numbers
        except ValueError:
            return number_str 

def chunk_text_by_sentences(text: str, max_words: int = 50) -> List[str]:
    """
    Split text into chunks, breaking at sentence boundaries after reaching max_words
    """
    # Split text into sentences using regex to handle multiple punctuation marks
    sentences = re.split(r'([.!?]+\s*)', text)
    
    chunks = []
    current_chunk = ""
    current_word_count = 0
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i].strip()
        if not sentence:
            i += 1
            continue
            
        # Add punctuation if it exists
        if i + 1 < len(sentences) and re.match(r'[.!?]+\s*', sentences[i + 1]):
            sentence += sentences[i + 1]
            i += 2
        else:
            i += 1
        
        sentence_words = len(sentence.split())
        
        # If adding this sentence would exceed max_words, start new chunk
        if current_word_count > 0 and current_word_count + sentence_words > max_words:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_word_count = sentence_words
        else:
            current_chunk += " " + sentence if current_chunk else sentence
            current_word_count += sentence_words
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def adaptive_chunk_text(text: str, max_words: int = 50, reduce_on_error: bool = True) -> List[str]:
    """
    Adaptively chunk text, reducing chunk size if needed
    """
    chunks = chunk_text_by_sentences(text, max_words)
    
    if reduce_on_error and any(len(chunk.split()) > max_words for chunk in chunks):
        # Recursively try with smaller chunk size
        return adaptive_chunk_text(text, max_words - 10, reduce_on_error)
    
    return chunks

def validate_text_input(text: str, max_chars: int = 13000) -> tuple[bool, str]:
    """
    Validate text input for TTS generation
    """
    if not text or not text.strip():
        return False, "Text content is required"
    
    if len(text.strip()) < 10:
        return False, "Text is too short (minimum 10 characters)"
        
    if len(text) > max_chars:
        return False, f"Text is too long (maximum {max_chars} characters)"
    
    return True, "Text validation passed" 