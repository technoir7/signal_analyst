"""
Cohort-Level Drift Analysis.

Aggregates Wayback signals across a peer cohort to detect:
- Convergence (everyone doing X)
- Divergence (split strategies)
- Temporal shifts (T-1 year vs T0)

Processing Flow:
1. Input: List of peer URLs
2. For each peer:
   - Fetch T0 (Current) snapshot (or live if we want, but Wayback is safer for fairness)
   - Fetch T-1 (Year ago) snapshot
   - Compute delta (SignalDelta)
3. Aggregate:
   - Compute stats (% change in density, auth, trust)
   - Identify outliers
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from loguru import logger
from utils.wayback import list_snapshots, _select_closest_snapshot, fetch_snapshot_html, extract_wayback_signals

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class PeerDriftProfile:
    """Drift profile for a single peer."""
    def __init__(self, url: str, name: str):
        self.url = url
        self.name = name
        self.t0_signals: Dict[str, Any] = {}
        self.t1_signals: Dict[str, Any] = {}
        self.has_history = False
        
    def get_delta(self, key: str) -> Any:
        """Get change from T1 -> T0."""
        v0 = self.t0_signals.get(key)
        v1 = self.t1_signals.get(key)
        
        # Boolean transition
        if isinstance(v0, bool) and isinstance(v1, bool):
            if v0 and not v1: return "gained"
            if not v0 and v1: return "lost"
            return "stable"
            
        # Numeric delta
        if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
            return v0 - v1
            
        return None

# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def process_peer_history(peer: Dict[str, str], t1_days: int = 365) -> PeerDriftProfile:
    """
    Fetch history for a single peer (synchronous for now).
    Returns PeerDriftProfile.
    """
    url = peer["url"]
    name = peer["name"]
    profile = PeerDriftProfile(url, name)
    
    try:
        now = datetime.now()
        t1_date = now - timedelta(days=t1_days)
        
        # 1. Fetch T0 (Recent - last 30 days)
        # We prefer an archive snapshot over live scrape to ensure comparability (apples-to-apples artifacts)
        # and avoid bot blocks on live sites.
        t0_snaps = list_snapshots(url, limit=5)
        t0_snap = _select_closest_snapshot(t0_snaps, now)
        
        # 2. Fetch T1 (Historical)
        if t0_snap:
            # Look for snapshot around t1_date
            from_ts = (t1_date - timedelta(days=30)).strftime("%Y%m%d")
            to_ts = (t1_date + timedelta(days=30)).strftime("%Y%m%d")
            t1_snaps = list_snapshots(url, from_ts=from_ts, to_ts=to_ts, limit=5)
            t1_snap = _select_closest_snapshot(t1_snaps, t1_date)
            
            # 3. Extract Signals
            if t0_snap:
                html0 = fetch_snapshot_html(t0_snap["timestamp"], t0_snap["original"])
                if html0:
                    profile.t0_signals = extract_wayback_signals(html0)
            
            if t1_snap:
                html1 = fetch_snapshot_html(t1_snap["timestamp"], t1_snap["original"])
                if html1:
                    profile.t1_signals = extract_wayback_signals(html1)
                    profile.has_history = True
                    
    except Exception as e:
        logger.error(f"Error processing history for {url}: {e}")
        
    return profile


def analyze_cohort_drift(peers: List[Dict[str, str]]) -> List[PeerDriftProfile]:
    """
    Process full cohort.
    
    For 8 peers, this might take ~30-60s sequentially.
    TODO: Parallelize with ThreadPoolExecutor if needed.
    """
    profiles = []
    logger.info(f"Analyzing drift for {len(peers)} peers...")
    
    for peer in peers:
        logger.info(f"  Fetching history for {peer['name']}...")
        profile = process_peer_history(peer)
        profiles.append(profile)
        
    return profiles
