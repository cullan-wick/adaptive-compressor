import requests
import time
import json
import os

# CONFIGURATION
API_URL = "http://127.0.0.1:8000"
BOOK_ID = 1  # <--- MAKE SURE THIS MATCHES YOUR DATABASE ID
READING_SPEED = 250

# TEST CASES (Minutes to summarize)
TEST_CASES = [5, 15, 30, 60]

def run_benchmark():
    print(f"--- STARTING BENCHMARK FOR BOOK ID {BOOK_ID} ---")
    
    # Store results to print a clean table at the end
    final_results = []

    for minutes in TEST_CASES:
        target_words = minutes * READING_SPEED
        
        # Progress Indicator (So you know it's working)
        print(f"Testing {minutes} min summary (~{target_words} words)... ", end="", flush=True)
        
        start_time = time.time()
        
        try:
            # Hit the API
            response = requests.post(
                f"{API_URL}/summarize/{BOOK_ID}?time_limit={minutes}&wpm={READING_SPEED}",
                timeout=300 # 5 minute timeout
            )
            response.raise_for_status()
            data = response.json()
            
            actual_words = data['final_summary_words']
            duration = round(time.time() - start_time, 2)
            
            # Calculate Error
            diff = actual_words - target_words
            error_percent = round((diff / target_words) * 100, 2)
            
            # Success Message
            print(f"DONE in {duration}s. (Actual: {actual_words}, Error: {error_percent}%)")
            
            # Save data for the final table
            final_results.append({
                "mins": minutes,
                "target": target_words,
                "actual": actual_words,
                "error": error_percent,
                "time": duration
            })
            
            # Save the text for manual review
            filename = f"benchmark_summary_{minutes}min.md"
            with open(filename, "w") as f:
                f.write(data['condensed_content'])
            
        except Exception as e:
            print(f"\nFAILED: {e}")
            final_results.append({
                "mins": minutes,
                "target": target_words,
                "actual": "FAIL",
                "error": "N/A",
                "time": "N/A"
            })

    # --- PRINT FINAL TABLE ---
    print("\n" + "="*80)
    print(f"{'Target (Mins)':<15} {'Target (Words)':<15} {'Actual (Words)':<15} {'Error %':<10} {'Time (s)':<10}")
    print("-" * 80)
    
    for res in final_results:
        print(f"{res['mins']:<15} {res['target']:<15} {res['actual']:<15} {res['error']:<10} {res['time']:<10}")
    print("="*80)

if __name__ == "__main__":
    run_benchmark()