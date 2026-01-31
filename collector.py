#!/usr/bin/env python3
"""
Polymarket Activity Collector & Analyzer
Interactive menu-driven application for wallet analysis and visualization
"""

import requests
import csv
import time
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration - paths relative to script location
SCRIPT_DIR = Path(__file__).parent.resolve()
WALLET_FILE = SCRIPT_DIR / "wallets.txt"
OUTPUT_ROOT = SCRIPT_DIR / "data"
PLOTS_DIR = SCRIPT_DIR / "plots"
CYCLES_DIR = SCRIPT_DIR / "cycles"

# Ensure directories exist
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(CYCLES_DIR, exist_ok=True)

# Default wallets (used if wallets.txt doesn't exist)
DEFAULT_WALLETS = {
    "gabagool22": "0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d",
    "wallet2": "0x336848a1a1cb00348020c9457676f34d882f21cd",
    "account88888": "0x7f69983eb28245bba0d5083502a78744a8f66162",
    "wallet3": "0x63ce342161250d705dc0b16df89036c8e5f9ba9a",
    "distinct-baguette": "0xe00740bce98a594e26861838885ab310ec3b548c",
    "sherlockhomie": "0xd44e29936409019f93993de8bd603ef6cb1bb15e",
    "kingofcoinflips": "0xe9c6312464b52aa3eff13d822b003282075995c9",
    "BoshBashBish": "0x29bc82f761749e67fa00d62896bc6855097b683c",
    "wallet4": "0xf247584e41117bbbe4cc06e4d2c95741792a5216",
    "wallet5": "0x1ff49fdcb6685c94059b65620f43a683be0ce7a5",
    "gab_inv": "0xf444220e8d32f456c39b6b727e7bb5bc41d8c970",
}


# ============================================================================
# API & DATA COLLECTION FUNCTIONS (Original)
# ============================================================================

def get_all_user_activity(wallet_address, max_records=10000):
    """Fetch all user activity from Polymarket API with pagination"""
    url = "https://data-api.polymarket.com/activity"
    all_activities = []
    limit = 500
    offset = 0
    
    print(f"Fetching data for wallet: {wallet_address}")
    print(f"Max records: {max_records}\n")
    
    while len(all_activities) < max_records and offset <= 10000:
        params = {
            "user": wallet_address,
            "limit": limit,
            "offset": offset,
            "sortBy": "TIMESTAMP",
            "sortDirection": "DESC"
        }
        
        try:
            print(f"Request: offset={offset}, limit={limit}...", end=" ")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or len(data) == 0:
                print("No more data available.")
                break
            
            print(f"Got {len(data)} records (total: {len(all_activities) + len(data)})")
            all_activities.extend(data)
            
            if len(data) < limit:
                print("Received last page of data.")
                break
            
            offset += limit
            time.sleep(0.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            print(f"\nRequest error: {e}")
            break
    
    print(f"\nTotal records collected: {len(all_activities)}")
    return all_activities


def remove_duplicates(activities):
    """Remove duplicates based on transactionHash"""
    seen = set()
    unique_activities = []
    duplicates_count = 0
    
    for activity in activities:
        tx_hash = activity.get('transactionHash')
        
        if tx_hash:
            unique_key = tx_hash
        else:
            # For non-transaction activities (SPLIT, MERGE, etc)
            unique_key = (
                activity.get('timestamp'),
                activity.get('type'),
                activity.get('market', {}).get('slug') if isinstance(activity.get('market'), dict) else None,
                activity.get('side')
            )
        
        if unique_key not in seen:
            seen.add(unique_key)
            unique_activities.append(activity)
        else:
            duplicates_count += 1
    
    if duplicates_count > 0:
        print(f"Removed {duplicates_count} duplicates")
    
    return unique_activities


def group_by_market(activities):
    """Group activities by market slug"""
    markets = defaultdict(list)
    for activity in activities:
        # API returns slug directly in activity, not in nested 'market' dict
        slug = activity.get('slug')
        if slug:
            markets[slug].append(activity)
    return dict(markets)


def save_market_to_csv(market_slug, activities, output_dir):
    """Save market activities to CSV file (only if >=30 TRADE records)"""
    if not activities:
        return None
    
    # Count TRADE records
    trade_count = sum(1 for a in activities if a.get('type') == 'TRADE')
    
    # Skip markets with less than 30 trades
    if trade_count < 30:
        return {'slug': market_slug, 'trades': trade_count, 'skipped': True}
    
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{market_slug}.csv")
    
    fieldnames = [
        'timestamp', 'datetime', 'type', 'side', 'proxyWallet',
        'conditionId', 'asset', 'outcomeIndex', 'outcome',
        'size', 'usdcSize', 'price', 'transactionHash',
        'title', 'slug', 'eventSlug', 'icon',
        'name', 'pseudonym', 'bio', 'profileImage', 'profileImageOptimized'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for activity in activities:
            # API returns all data directly in activity object
            row = {
                'timestamp': activity.get('timestamp', ''),
                'datetime': datetime.fromtimestamp(
                    int(activity.get('timestamp', 0)),
                    tz=timezone.utc
                ).strftime('%Y-%m-%d %H:%M:%S') if activity.get('timestamp') else '',
                'type': activity.get('type', ''),
                'side': activity.get('side', ''),
                'proxyWallet': activity.get('proxyWallet', ''),
                'conditionId': activity.get('conditionId', ''),
                'asset': activity.get('asset', ''),
                'outcomeIndex': activity.get('outcomeIndex', ''),
                'outcome': activity.get('outcome', ''),
                'size': activity.get('size', ''),
                'usdcSize': activity.get('usdcSize', ''),
                'price': activity.get('price', ''),
                'transactionHash': activity.get('transactionHash', ''),
                'title': activity.get('title', ''),
                'slug': activity.get('slug', ''),
                'eventSlug': activity.get('eventSlug', ''),
                'icon': activity.get('icon', ''),
                'name': activity.get('name', ''),
                'pseudonym': activity.get('pseudonym', ''),
                'bio': activity.get('bio', ''),
                'profileImage': activity.get('profileImage', ''),
                'profileImageOptimized': activity.get('profileImageOptimized', ''),
            }
            writer.writerow(row)
    
    return filepath


def process_wallet(wallet_name, wallet_address, max_records=10000):
    """Main processing function for a wallet"""
    print(f"\n{'='*70}")
    print(f"PROCESSING WALLET: {wallet_name}")
    print(f"Address: {wallet_address}")
    print(f"{'='*70}\n")
    
    # Fetch data
    activities = get_all_user_activity(wallet_address, max_records)
    
    if not activities:
        print("No activities found.")
        return
    
    # Remove duplicates
    activities = remove_duplicates(activities)
    
    # Group by market
    markets = group_by_market(activities)
    print(f"\nFound {len(markets)} unique markets")
    
    # Save to CSV
    output_dir = os.path.join(OUTPUT_ROOT, wallet_name)
    
    print(f"\nSaving to: {output_dir}")
    saved_count = 0
    skipped_markets = []
    
    for market_slug, market_activities in markets.items():
        result = save_market_to_csv(market_slug, market_activities, output_dir)
        if result and isinstance(result, dict) and result.get('skipped'):
            skipped_markets.append((result['slug'], result['trades']))
        elif result:
            saved_count += 1
            print(f"  ✓ {market_slug}.csv ({len(market_activities)} records)")
    
    print(f"\n{'='*70}")
    print(f"COMPLETED: {saved_count} markets saved to {output_dir}")
    
    if skipped_markets:
        print(f"\n⚠️  SKIPPED {len(skipped_markets)} markets (too few trades for analysis):")
        for slug, count in skipped_markets:
            print(f"  ✗ {slug} ({count} trades < 30 minimum)")
    
    print(f"{'='*70}\n")


# ============================================================================
# CYCLIC COLLECTION FUNCTIONS
# ============================================================================

def configure_cycle_mode():
    """Configure cycle parameters interactively"""
    print("\n" + "="*70)
    print(" "*20 + "CYCLE CONFIGURATION")
    print("="*70 + "\n")
    
    while True:
        try:
            interval = input("Interval in minutes (e.g., 1, 5, 10): ").strip()
            if not interval:
                print("❌ Interval cannot be empty")
                continue
            interval_minutes = int(interval)
            if interval_minutes < 1:
                print("❌ Interval must be at least 1 minute")
                continue
            break
        except ValueError:
            print("❌ Please enter a valid number")
    
    while True:
        try:
            cycles = input("Number of cycles (e.g., 10, 50, 100): ").strip()
            if not cycles:
                print("❌ Number of cycles cannot be empty")
                continue
            num_cycles = int(cycles)
            if num_cycles < 1:
                print("❌ Must have at least 1 cycle")
                continue
            break
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Estimate total time
    total_minutes = interval_minutes * num_cycles
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    print(f"\n{'='*70}")
    print("SUMMARY:")
    print(f"  Interval: {interval_minutes} minute(s)")
    print(f"  Cycles: {num_cycles}")
    print(f"  Estimated total time: {hours}h {minutes}m")
    print(f"{'='*70}\n")
    
    return interval_minutes, num_cycles


def run_cyclic_collection(wallet_name, wallet_address, interval_minutes, num_cycles):
    """Run cyclic data collection with merging of repeated markets"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    cycle_dir = os.path.join(CYCLES_DIR, f"{wallet_name}_{timestamp}")
    os.makedirs(cycle_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"STARTING CYCLIC COLLECTION")
    print(f"Output directory: {cycle_dir}")
    print(f"{'='*70}\n")
    
    # Storage for tracking markets across cycles
    market_history = defaultdict(list)  # {market_slug: [cycle_data, ...]}
    
    for cycle_num in range(1, num_cycles + 1):
        print(f"\n{'='*70}")
        print(f"CYCLE {cycle_num}/{num_cycles}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        # Collect data for current cycle
        activities = get_all_user_activity(wallet_address, max_records=10000)
        
        if not activities:
            print("⚠️  No activities found in this cycle")
        else:
            activities = remove_duplicates(activities)
            markets = group_by_market(activities)
            
            print(f"\nFound {len(markets)} markets in cycle {cycle_num}")
            
            # Save cycle data to individual directory
            cycle_subdir = os.path.join(cycle_dir, f"cycle_{cycle_num:03d}")
            os.makedirs(cycle_subdir, exist_ok=True)
            
            # Update market history
            for market_slug, market_activities in markets.items():
                market_history[market_slug].append({
                    'cycle': cycle_num,
                    'activities': market_activities,
                    'timestamp': datetime.now(),
                    'cycle_dir': cycle_subdir
                })
                
                # Save to cycle-specific CSV
                trade_count = sum(1 for a in market_activities if a.get('type') == 'TRADE')
                if trade_count >= 30:
                    save_market_to_csv(market_slug, market_activities, cycle_subdir)
                    print(f"  ✓ {market_slug} ({trade_count} trades)")
        
        # Wait for next cycle (skip on last cycle)
        if cycle_num < num_cycles:
            wait_seconds = interval_minutes * 60
            print(f"\n⏳ Waiting {interval_minutes} minute(s) until next cycle...")
            print(f"   Next cycle starts at: {(datetime.now() + timedelta(seconds=wait_seconds)).strftime('%H:%M:%S')}")
            
            # Progress indicator during wait
            for remaining in range(wait_seconds, 0, -10):
                if remaining <= wait_seconds:
                    mins = remaining // 60
                    secs = remaining % 60
                    print(f"   Time remaining: {mins:02d}:{secs:02d}", end='\r')
                    time.sleep(min(10, remaining))
            print(" " * 50, end='\r')  # Clear the line
    
    # Merge results after all cycles complete
    print(f"\n{'='*70}")
    print("ALL CYCLES COMPLETED - MERGING RESULTS")
    print(f"{'='*70}\n")
    merge_cycle_results(cycle_dir, market_history, wallet_name)
    
    return cycle_dir


def merge_cycle_results(cycle_dir, market_history, wallet_name):
    """Merge cycle results into unified files for recurring markets"""
    merged_dir = os.path.join(cycle_dir, "merged")
    os.makedirs(merged_dir, exist_ok=True)
    
    print(f"Merging results for {len(market_history)} unique markets...\n")
    
    merged_count = 0
    single_cycle_count = 0
    
    for market_slug, cycle_data_list in sorted(market_history.items()):
        cycles_found = len(cycle_data_list)
        
        # Check if market appeared in multiple cycles
        if cycles_found < 2:
            single_cycle_count += 1
            continue
        
        # Collect all activities from all cycles
        all_activities = []
        for cycle_data in cycle_data_list:
            all_activities.extend(cycle_data['activities'])
        
        # Remove duplicates based on transactionHash
        all_activities = remove_duplicates(all_activities)
        
        # Count trades
        trade_count = sum(1 for a in all_activities if a.get('type') == 'TRADE')
        
        # Save merged file if meets minimum threshold
        if trade_count >= 30:
            output_path = save_market_to_csv(market_slug, all_activities, merged_dir)
            if output_path:
                merged_count += 1
                cycle_nums = [cd['cycle'] for cd in cycle_data_list]
                print(f"  ✓ {market_slug}")
                print(f"    Cycles: {cycle_nums} ({cycles_found} occurrences)")
                print(f"    Trades: {trade_count}, Total records: {len(all_activities)}")
    
    print(f"\n{'='*70}")
    print(f"MERGE SUMMARY:")
    print(f"  Markets merged (2+ cycles): {merged_count}")
    print(f"  Single-cycle markets (not merged): {single_cycle_count}")
    print(f"  Output directory: {merged_dir}")
    print(f"{'='*70}\n")
    
    # Create summary report
    summary_file = os.path.join(cycle_dir, "summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"CYCLIC COLLECTION SUMMARY\n")
        f.write(f"{'='*70}\n\n")
        f.write(f"Wallet: {wallet_name}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total markets found: {len(market_history)}\n")
        f.write(f"Markets merged (2+ cycles): {merged_count}\n")
        f.write(f"Single-cycle markets: {single_cycle_count}\n\n")
        f.write(f"{'='*70}\n")
        f.write(f"MARKET DETAILS:\n")
        f.write(f"{'='*70}\n\n")
        
        for market_slug, cycle_data_list in sorted(market_history.items()):
            cycles_found = len(cycle_data_list)
            cycle_nums = [cd['cycle'] for cd in cycle_data_list]
            f.write(f"{market_slug}\n")
            f.write(f"  Cycles: {cycle_nums} ({cycles_found} occurrences)\n\n")
    
    print(f"📄 Summary report saved to: {summary_file}\n")


# ============================================================================
# WALLET MANAGEMENT
# ============================================================================

def ensure_wallet_file(file_path, default_wallets):
    """Create wallet file if it doesn't exist"""
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            for name, addr in default_wallets.items():
                f.write(f"{name},{addr}\n")
        print(f"Created {file_path} with {len(default_wallets)} default wallets")


def load_wallets(file_path, default_wallets):
    """Load wallets from file in format: name,address"""
    ensure_wallet_file(file_path, default_wallets)
    wallets = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:
                name, addr = line.split(",", 1)
            else:
                # Fallback to space separator
                parts = line.split()
                if len(parts) >= 2:
                    name, addr = parts[0], parts[1]
                else:
                    continue
            name = name.strip()
            addr = addr.strip()
            if name and addr:
                wallets[name] = addr
    return wallets


def append_wallet(file_path, name, address):
    """Add new wallet to file for persistence"""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{name},{address}\n")


def add_new_wallet_interactive(wallets, wallet_file):
    """Interactive wallet addition"""
    print("\n" + "="*70)
    print("ADD NEW WALLET")
    print("="*70)
    
    name = input("\nEnter wallet name (e.g., myWallet): ").strip()
    if not name:
        print("❌ Error: wallet name cannot be empty")
        input("\nPress Enter to continue...")
        return wallets
    
    if name in wallets:
        print(f"⚠️  Warning: wallet '{name}' already exists")
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite not in ("y", "yes"):
            input("\nPress Enter to continue...")
            return wallets
    
    address = input("Enter wallet address (0x...): ").strip()
    if not address:
        print("❌ Error: address cannot be empty")
        input("\nPress Enter to continue...")
        return wallets
    
    if not address.startswith("0x") or len(address) < 10:
        print("⚠️  Warning: address looks unusual, please verify")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            input("\nPress Enter to continue...")
            return wallets
    
    wallets[name] = address
    append_wallet(wallet_file, name, address)
    print(f"\n✅ Added wallet: {name} → {address}")
    input("\nPress Enter to continue...")
    return wallets


# ============================================================================
# PLOTTING FUNCTIONS
# ============================================================================

def load_csv_data(csv_path):
    """Load and parse CSV file"""
    trades = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['type'] == 'TRADE':
                try:
                    trades.append({
                        'timestamp': int(row['timestamp']),
                        'datetime': row['datetime'],
                        'outcome': row['outcome'],
                        'size': float(row['size']) if row['size'] else 0,
                        'usdcSize': float(row['usdcSize']) if row['usdcSize'] else 0,
                        'price': float(row['price']) if row['price'] else 0,
                    })
                except (ValueError, KeyError):
                    continue
    return trades


def plot_market_analysis(csv_path, output_path=None):
    """Create dual plot: purchases scatter + contracts accumulation"""
    trades = load_csv_data(csv_path)
    
    if not trades:
        print("❌ No trade data found in CSV")
        return None
    
    # Separate UP and DOWN trades
    up_trades = [t for t in trades if t['outcome'].lower() == 'up']
    down_trades = [t for t in trades if t['outcome'].lower() == 'down']
    
    # Prepare data for plotting - SWAP X and Y axes
    # X = price (0-1), Y = timestamp
    up_prices = [t['price'] for t in up_trades]
    up_times = [t['timestamp'] for t in up_trades]
    up_usdc = [t['usdcSize'] for t in up_trades]
    
    down_prices = [t['price'] for t in down_trades]
    down_times = [t['timestamp'] for t in down_trades]
    down_usdc = [t['usdcSize'] for t in down_trades]
    
    # Calculate cumulative contracts
    up_contracts_cumsum = []
    down_contracts_cumsum = []
    up_sum = 0
    down_sum = 0
    
    all_times = sorted(set([t['timestamp'] for t in trades]))
    
    for ts in all_times:
        up_sum += sum(t['size'] for t in up_trades if t['timestamp'] == ts)
        down_sum += sum(t['size'] for t in down_trades if t['timestamp'] == ts)
        up_contracts_cumsum.append(up_sum)
        down_contracts_cumsum.append(down_sum)
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(f'Market Analysis: {Path(csv_path).stem}', fontsize=16, fontweight='bold')
    
    # Plot 1: Purchase scatter (X=time, Y=price, point size = USDC)
    if up_times:
        ax1.scatter(up_times, up_prices, c='green', s=[u*10 for u in up_usdc], 
                   alpha=0.6, label='UP', edgecolors='darkgreen', linewidth=0.5)
    if down_times:
        ax1.scatter(down_times, down_prices, c='red', s=[d*10 for d in down_usdc], 
                   alpha=0.6, label='DOWN', edgecolors='darkred', linewidth=0.5)
    
    ax1.set_xlabel('Timestamp', fontsize=12)
    ax1.set_ylabel('Price (0.01 - 1.00)', fontsize=12)
    ax1.set_ylim(0, 1)  # Price range 0-1
    ax1.set_title('Purchases: X=Time, Y=Price (point size = USDC amount)', fontsize=14)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Cumulative contracts
    ax2.plot(all_times, up_contracts_cumsum, color='green', linewidth=2, 
            marker='o', markersize=4, label='UP Contracts', alpha=0.8)
    ax2.plot(all_times, down_contracts_cumsum, color='red', linewidth=2, 
            marker='o', markersize=4, label='DOWN Contracts', alpha=0.8)
    
    ax2.set_xlabel('Timestamp', fontsize=12)
    ax2.set_ylabel('Cumulative Contracts', fontsize=12)
    ax2.set_title('Cumulative Contract Accumulation', fontsize=14)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # Add statistics text box
    stats_text = f"""
    Total Trades: {len(trades)}
    UP: {len(up_trades)} trades, {sum(t['size'] for t in up_trades):.1f} contracts, ${sum(up_usdc):.2f}
    DOWN: {len(down_trades)} trades, {sum(t['size'] for t in down_trades):.1f} contracts, ${sum(down_usdc):.2f}
    """
    ax2.text(0.02, 0.98, stats_text.strip(), transform=ax2.transAxes, 
            fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', 
            facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save plot
    if output_path is None:
        output_path = os.path.join(PLOTS_DIR, f"{Path(csv_path).stem}.png")
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


# ============================================================================
# MENU SYSTEM
# ============================================================================

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_main_menu():
    """Display main menu"""
    clear_screen()
    print("\n" + "="*70)
    print(" "*15 + "🚀 POLYMARKET COLLECTOR & ANALYZER 🚀")
    print("="*70)
    print("\n[1] Run Wallet Analysis")
    print("[2] Add New Wallet")
    print("[3] Create Market Plot")
    print("[4] Exit")
    print("\n" + "="*70)


def select_wallet_menu(wallets):
    """Display wallet selection menu"""
    clear_screen()
    print("\n" + "="*70)
    print(" "*20 + "SELECT WALLET")
    print("="*70 + "\n")
    
    wallet_list = list(wallets.items())
    for idx, (name, addr) in enumerate(wallet_list, 1):
        print(f"[{idx}] {name}")
        print(f"    {addr[:10]}...{addr[-6:]}")
    
    print(f"\n[{len(wallet_list) + 1}] ← Back to Main Menu")
    print("\n" + "="*70)
    
    while True:
        choice = input("\nSelect wallet (number): ").strip()
        if not choice:
            continue
        
        try:
            num = int(choice)
            if num == len(wallet_list) + 1:
                return None  # Back to main menu
            if 1 <= num <= len(wallet_list):
                return wallet_list[num - 1]
            else:
                print(f"❌ Please enter 1-{len(wallet_list) + 1}")
        except ValueError:
            print("❌ Please enter a valid number")


def select_blogger_menu():
    """Select blogger (data folder)"""
    clear_screen()
    print("\n" + "="*70)
    print(" "*20 + "SELECT BLOGGER")
    print("="*70 + "\n")
    
    if not os.path.exists(OUTPUT_ROOT):
        print("❌ No data directory found")
        input("\nPress Enter to continue...")
        return None
    
    bloggers = [d for d in os.listdir(OUTPUT_ROOT) 
                if os.path.isdir(os.path.join(OUTPUT_ROOT, d))]
    
    if not bloggers:
        print("❌ No blogger data found. Run analysis first!")
        input("\nPress Enter to continue...")
        return None
    
    for idx, blogger in enumerate(bloggers, 1):
        csv_count = len([f for f in os.listdir(os.path.join(OUTPUT_ROOT, blogger)) 
                        if f.endswith('.csv')])
        print(f"[{idx}] {blogger} ({csv_count} markets)")
    
    print(f"\n[{len(bloggers) + 1}] ← Back to Main Menu")
    print("\n" + "="*70)
    
    while True:
        choice = input("\nSelect blogger (number): ").strip()
        if not choice:
            continue
        
        try:
            num = int(choice)
            if num == len(bloggers) + 1:
                return None
            if 1 <= num <= len(bloggers):
                return bloggers[num - 1]
            else:
                print(f"❌ Please enter 1-{len(bloggers) + 1}")
        except ValueError:
            print("❌ Please enter a valid number")


def select_market_menu(blogger):
    """Select market CSV file"""
    clear_screen()
    print("\n" + "="*70)
    print(f" "*15 + f"SELECT MARKET ({blogger})")
    print("="*70 + "\n")
    
    blogger_dir = os.path.join(OUTPUT_ROOT, blogger)
    markets = [f for f in os.listdir(blogger_dir) if f.endswith('.csv')]
    
    if not markets:
        print("❌ No market data found")
        input("\nPress Enter to continue...")
        return None
    
    markets.sort()
    
    # Display in pages if too many
    page_size = 20
    page = 0
    max_pages = (len(markets) - 1) // page_size + 1
    
    while True:
        clear_screen()
        print("\n" + "="*70)
        print(f" "*15 + f"SELECT MARKET ({blogger})")
        print(f" "*20 + f"Page {page + 1}/{max_pages}")
        print("="*70 + "\n")
        
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(markets))
        
        for i in range(start_idx, end_idx):
            csv_path = os.path.join(blogger_dir, markets[i])
            try:
                # Count lines in CSV (subtract 1 for header)
                with open(csv_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f) - 1
                print(f"[{i - start_idx + 1}] {markets[i]} ({line_count} records)")
            except Exception:
                print(f"[{i - start_idx + 1}] {markets[i]} (? records)")
        
        print(f"\n[N] Next page" if page < max_pages - 1 else "")
        print(f"[P] Previous page" if page > 0 else "")
        print("[B] ← Back to Blogger Selection")
        print("\n" + "="*70)
        
        choice = input("\nSelect market (number/N/P/B): ").strip().lower()
        
        if choice == 'n' and page < max_pages - 1:
            page += 1
            continue
        elif choice == 'p' and page > 0:
            page -= 1
            continue
        elif choice == 'b':
            return None
        
        try:
            num = int(choice)
            if 1 <= num <= (end_idx - start_idx):
                return os.path.join(blogger_dir, markets[start_idx + num - 1])
            else:
                print(f"❌ Please enter 1-{end_idx - start_idx}")
                time.sleep(1)
        except ValueError:
            print("❌ Invalid input")
            time.sleep(1)


def run_analysis_flow(wallets, wallet_file):
    """Wallet analysis flow with mode selection"""
    while True:
        result = select_wallet_menu(wallets)
        if result is None:
            return  # Back to main menu
        
        wallet_name, wallet_addr = result
        
        # Mode selection menu
        clear_screen()
        print("\n" + "="*70)
        print(" "*20 + "SELECT MODE")
        print("="*70)
        print(f"\nWallet: {wallet_name}")
        print(f"Address: {wallet_addr[:10]}...{wallet_addr[-6:]}")
        print("\n" + "-"*70)
        print("\n[1] Single Run (collect data once)")
        print("[2] Cyclic Collection (repeat at intervals)")
        print("[3] ← Back to Wallet Selection")
        print("\n" + "="*70)
        
        mode = input("\nSelect mode (1-3): ").strip()
        
        if mode == '1':
            # Single run mode (current behavior)
            clear_screen()
            process_wallet(wallet_name, wallet_addr, max_records=10000)
            input("\n✅ Analysis complete! Press Enter to continue...")
            
        elif mode == '2':
            # Cyclic collection mode
            interval_minutes, num_cycles = configure_cycle_mode()
            
            # Confirmation
            clear_screen()
            print(f"\n{'='*70}")
            print(" "*15 + "⚠️  CYCLIC COLLECTION CONFIRMATION")
            print(f"{'='*70}\n")
            print(f"Wallet: {wallet_name}")
            print(f"Interval: {interval_minutes} minute(s)")
            print(f"Cycles: {num_cycles}")
            print(f"Total time: ~{(interval_minutes * num_cycles) // 60}h {(interval_minutes * num_cycles) % 60}m")
            print(f"\n{'='*70}")
            
            confirm = input("\nStart cyclic collection? (y/N): ").strip().lower()
            if confirm in ('y', 'yes'):
                clear_screen()
                cycle_dir = run_cyclic_collection(wallet_name, wallet_addr, interval_minutes, num_cycles)
                
                print(f"\n{'='*70}")
                print("✅ CYCLIC COLLECTION COMPLETE!")
                print(f"{'='*70}")
                print(f"\nResults saved to: {cycle_dir}")
                print(f"  - Individual cycles: {cycle_dir}/cycle_XXX/")
                print(f"  - Merged data: {cycle_dir}/merged/")
                print(f"  - Summary report: {cycle_dir}/summary.txt")
                print(f"\n{'='*70}\n")
                
                input("Press Enter to continue...")
            else:
                print("\n❌ Cyclic collection cancelled")
                time.sleep(1)
                
        elif mode == '3':
            continue  # Back to wallet selection
        else:
            print("❌ Invalid option. Please select 1-3.")
            time.sleep(1)


def create_plot_flow():
    """Plot creation flow"""
    while True:
        # Select blogger
        blogger = select_blogger_menu()
        if blogger is None:
            return  # Back to main menu
        
        # Select market
        market_csv = select_market_menu(blogger)
        if market_csv is None:
            continue  # Back to blogger selection
        
        # Create plot
        clear_screen()
        print("\n" + "="*70)
        print("CREATING PLOT...")
        print("="*70 + "\n")
        
        output_path = plot_market_analysis(market_csv)
        
        if output_path:
            print(f"\n✅ Plot saved to: {output_path}")
        else:
            print("\n❌ Failed to create plot")
        
        # Ask if want to create another
        print("\n" + "="*70)
        choice = input("\nCreate another plot? (y/N): ").strip().lower()
        if choice not in ('y', 'yes'):
            return  # Back to main menu


def main_menu_loop():
    """Main application loop"""
    wallets = load_wallets(WALLET_FILE, DEFAULT_WALLETS)
    
    while True:
        print_main_menu()
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            run_analysis_flow(wallets, WALLET_FILE)
        elif choice == '2':
            wallets = add_new_wallet_interactive(wallets, WALLET_FILE)
        elif choice == '3':
            create_plot_flow()
        elif choice == '4':
            clear_screen()
            print("\n👋 Goodbye!\n")
            break
        else:
            print("❌ Invalid option. Please select 1-4.")
            time.sleep(1)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main_menu_loop()
    except KeyboardInterrupt:
        clear_screen()
        print("\n\n👋 Interrupted by user. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
