#!/usr/bin/env python3
"""
Batch Cache Population Script

This script implements true prompt caching by calling the /analyze endpoint for each canonical question
and storing the actual endpoint responses in the cache. This ensures cached answers are always
consistent with the endpoint logic and up-to-date.

This is similar to OpenAI's prompt caching where responses are pre-computed and stored for identical queries.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from app.models import ConversationAnalysisRequest, ConversationAnalysisResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchCachePopulator:
    """Batch cache populator that calls the actual /analyze endpoint for each question."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8000",
                 timeout: float = 60.0,
                 max_retries: int = 3,
                 retry_delay: float = 2.0):
        """Initialize the batch cache populator.
        
        Args:
            base_url: Base URL of the FastAPI backend
            timeout: Timeout for each API call in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def load_canonical_questions(self, file_path: str) -> List[str]:
        """Load canonical questions from the preprocessed file.
        
        Args:
            file_path: Path to the questions file
            
        Returns:
            List of canonical questions
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Split by lines and filter out empty lines
            questions = [
                line.strip() 
                for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')
            ]
            
            logger.info(f"Loaded {len(questions)} canonical questions from {file_path}")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to load questions from {file_path}: {e}")
            return []
    
    async def call_analyze_endpoint(self, question: str) -> Dict[str, Any]:
        """Call the /analyze endpoint for a single question with retries.
        
        Args:
            question: The question to analyze
            
        Returns:
            The response from the /analyze endpoint
            
        Raises:
            Exception: If all retry attempts fail
        """
        request_data = ConversationAnalysisRequest(
            conversation=question,
            max_response_length=500,
            tone="professional",
            include_sources=True
        )
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Calling /analyze for: '{question[:50]}...' (attempt {attempt + 1})")
                
                response = await self.client.post(
                    f"{self.base_url}/analyze",
                    json=request_data.dict(),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully analyzed: '{question[:50]}...'")
                    return result
                else:
                    logger.warning(f"HTTP {response.status_code} for question: '{question[:50]}...'")
                    logger.warning(f"Response: {response.text}")
                    
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")
                        
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed for '{question[:50]}...': {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All attempts failed for '{question[:50]}...': {e}")
                    raise
    
    async def populate_cache_batch(self, questions: List[str], 
                                 batch_size: int = 5,
                                 delay_between_batches: float = 1.0) -> Dict[str, Any]:
        """Populate the cache by calling /analyze for each question in batches.
        
        Args:
            questions: List of questions to process
            batch_size: Number of questions to process concurrently
            delay_between_batches: Delay between batches in seconds
            
        Returns:
            Summary of the population process
        """
        total_questions = len(questions)
        successful = 0
        failed = 0
        failed_questions = []
        
        start_time = time.time()
        
        logger.info(f"Starting batch cache population for {total_questions} questions")
        logger.info(f"Batch size: {batch_size}, Delay between batches: {delay_between_batches}s")
        
        # Process questions in batches
        for i in range(0, total_questions, batch_size):
            batch = questions[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_questions + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} questions)")
            
            # Process batch concurrently
            tasks = [self.call_analyze_endpoint(question) for question in batch]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for question, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to process: '{question[:50]}...': {result}")
                        failed += 1
                        failed_questions.append(question)
                    else:
                        logger.info(f"Successfully cached: '{question[:50]}...'")
                        successful += 1
                        
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                failed += len(batch)
                failed_questions.extend(batch)
            
            # Delay between batches to avoid overwhelming the server
            if i + batch_size < total_questions:
                await asyncio.sleep(delay_between_batches)
        
        end_time = time.time()
        duration = end_time - start_time
        
        summary = {
            "total_questions": total_questions,
            "successful": successful,
            "failed": failed,
            "failed_questions": failed_questions,
            "duration_seconds": duration,
            "questions_per_second": total_questions / duration if duration > 0 else 0,
            "success_rate": successful / total_questions if total_questions > 0 else 0
        }
        
        logger.info(f"Batch cache population completed:")
        logger.info(f"  Total: {total_questions}, Success: {successful}, Failed: {failed}")
        logger.info(f"  Duration: {duration:.2f}s, Rate: {summary['questions_per_second']:.2f} q/s")
        logger.info(f"  Success rate: {summary['success_rate']:.2%}")
        
        return summary
    
    async def clear_cache_before_population(self) -> bool:
        """Clear the existing cache before populating with fresh data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Clearing existing cache before population...")
            
            response = await self.client.post(f"{self.base_url}/cache/clear")
            
            if response.status_code == 200:
                logger.info("Successfully cleared existing cache")
                return True
            else:
                logger.warning(f"Failed to clear cache: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics.
        
        Returns:
            Cache statistics
        """
        try:
            response = await self.client.get(f"{self.base_url}/cache/stats")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get cache stats: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

async def main():
    """Main function to run batch cache population."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch populate the answer cache by calling /analyze endpoint")
    parser.add_argument("--questions-file", 
                       default="../docs/questions_preprocessed",
                       help="Path to the canonical questions file")
    parser.add_argument("--base-url", 
                       default="http://localhost:8000",
                       help="Base URL of the FastAPI backend")
    parser.add_argument("--batch-size", 
                       type=int, 
                       default=5,
                       help="Number of questions to process concurrently")
    parser.add_argument("--delay", 
                       type=float, 
                       default=1.0,
                       help="Delay between batches in seconds")
    parser.add_argument("--clear-cache", 
                       action="store_true",
                       help="Clear existing cache before population")
    parser.add_argument("--timeout", 
                       type=float, 
                       default=60.0,
                       help="Timeout for each API call in seconds")
    
    args = parser.parse_args()
    
    # Resolve the questions file path
    script_dir = Path(__file__).parent
    questions_file = script_dir / args.questions_file
    
    if not questions_file.exists():
        logger.error(f"Questions file not found: {questions_file}")
        return 1
    
    async with BatchCachePopulator(
        base_url=args.base_url,
        timeout=args.timeout
    ) as populator:
        
        # Load canonical questions
        questions = populator.load_canonical_questions(str(questions_file))
        if not questions:
            logger.error("No questions loaded, exiting")
            return 1
        
        # Clear cache if requested
        if args.clear_cache:
            await populator.clear_cache_before_population()
        
        # Get initial cache stats
        initial_stats = await populator.get_cache_stats()
        logger.info(f"Initial cache stats: {initial_stats}")
        
        # Populate the cache
        summary = await populator.populate_cache_batch(
            questions=questions,
            batch_size=args.batch_size,
            delay_between_batches=args.delay
        )
        
        # Get final cache stats
        final_stats = await populator.get_cache_stats()
        logger.info(f"Final cache stats: {final_stats}")
        
        # Save summary to file
        summary_file = script_dir / "batch_population_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "arguments": vars(args),
                "initial_stats": initial_stats,
                "final_stats": final_stats,
                "summary": summary
            }, f, indent=2)
        
        logger.info(f"Summary saved to: {summary_file}")
        
        # Print final results
        print("\n" + "="*60)
        print("BATCH CACHE POPULATION COMPLETE")
        print("="*60)
        print(f"Total Questions: {summary['total_questions']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {summary['success_rate']:.2%}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Rate: {summary['questions_per_second']:.2f} questions/second")
        
        if summary['failed_questions']:
            print(f"\nFailed Questions ({len(summary['failed_questions'])}):")
            for q in summary['failed_questions'][:5]:  # Show first 5
                print(f"  - {q[:80]}...")
            if len(summary['failed_questions']) > 5:
                print(f"  ... and {len(summary['failed_questions']) - 5} more")
        
        return 0 if summary['failed'] == 0 else 1

if __name__ == "__main__":
    try:
        import datetime
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
