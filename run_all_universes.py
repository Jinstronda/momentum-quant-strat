"""Run backtests for all configured universes."""

import sys
from datetime import datetime
from pathlib import Path

from src.config import get_config, UNIVERSES


def run_all_universes():
    """Run backtest for each universe in configuration."""
    from main import run_backtest_for_universe
    
    config = get_config()
    universes = list(UNIVERSES.keys())
    
    print(f"\n{'='*80}")
    print(f"RUNNING BACKTESTS FOR ALL {len(universes)} UNIVERSES")
    print(f"{'='*80}")
    print(f"Start Date: {config['start_date'].date()}")
    print(f"End Date: {config['end_date'].date()}")
    print(f"Momentum: {config['momentum_type']}")
    print(f"Rebalance: {config['rebalance_frequency']}")
    print(f"Filter: {config['filter_type']}")
    print(f"{'='*80}\n")
    
    results = []
    
    for i, universe_name in enumerate(universes, 1):
        print(f"\n{'#'*80}")
        print(f"# UNIVERSE {i}/{len(universes)}: {universe_name}")
        print(f"{'#'*80}\n")
        
        try:
            # Create output directory name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            momentum_label = config['momentum_type']
            if momentum_label != 'POLYMORPHIC':
                momentum_label = f"{momentum_label}{config['momentum_period']}d"
            else:
                momentum_label = f"{momentum_label}{config['momentum_period']}d"
            
            freq_label = 'W' if config['rebalance_frequency'] == 'weekly' else 'M'
            output_dir = f"output/{timestamp}_{universe_name}_{momentum_label}_{freq_label}_Top{config['top_n']}"
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Run backtest
            run_backtest_for_universe(universe_name, config, output_dir)
            
            results.append({
                'universe': universe_name,
                'status': 'SUCCESS',
                'output_dir': output_dir
            })
            
            print(f"\n[OK] {universe_name} backtest completed successfully")
            print(f"     Output: {output_dir}\n")
            
        except Exception as e:
            print(f"\n[ERROR] {universe_name} backtest failed: {e}\n")
            results.append({
                'universe': universe_name,
                'status': 'FAILED',
                'error': str(e)
            })
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"BACKTEST SUMMARY")
    print(f"{'='*80}\n")
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    
    print(f"Total: {len(results)} universes")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}\n")
    
    for result in results:
        status_symbol = "[OK]" if result['status'] == 'SUCCESS' else "[FAIL]"
        print(f"{status_symbol} {result['universe']}")
        if result['status'] == 'SUCCESS':
            print(f"         Output: {result['output_dir']}")
        else:
            print(f"         Error: {result['error']}")
    
    print(f"\n{'='*80}\n")
    
    return results


if __name__ == "__main__":
    results = run_all_universes()
    
    # Exit with error code if any failed
    failed_count = sum(1 for r in results if r['status'] == 'FAILED')
    sys.exit(1 if failed_count > 0 else 0)

