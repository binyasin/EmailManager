#!/usr/bin/env python3
"""
eBay Account Manager — OpenClaw Integration
Monitors orders, listings, messages, and generates reports.
Connects to eBay APIs and local SQLite for tracking.
"""

import os
import json
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import requests
import re
import base64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("EbayManager")

# --------------------------------------------------
# Configuration
# --------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ebay_data.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ebay_config.json")

# eBay API endpoints
EBAY_API_BASE = "https://api.ebay.com"
EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/token"

# --------------------------------------------------
# Data Models
# --------------------------------------------------

@dataclass
class EbayOrder:
    order_id: str
    item_title: str
    buyer_username: str
    sale_price: float
    shipping_cost: float
    order_status: str  # pending, shipped, delivered, cancelled
    purchase_date: str
    shipping_address: str
    tracking_number: str = ""
    last_updated: str = ""

@dataclass
class EbayListing:
    listing_id: str
    title: str
    price: float
    quantity: int
    quantity_sold: int
    status: str  # active, ended, out_of_stock
    views: int
    watchers: int
    start_date: str
    end_date: str

@dataclass
class EbayMessage:
    message_id: str
    from_user: str
    subject: str
    body: str
    item_id: str = ""
    sent_date: str = ""
    replied: bool = False

@dataclass
class PriceAlert:
    alert_id: int
    search_term: str
    max_price: float
    category: str = ""
    active: bool = True
    last_checked: str = ""

# --------------------------------------------------
# Database Layer
# --------------------------------------------------

class EbayDatabase:
    """SQLite database for all eBay data."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                item_title TEXT,
                buyer_username TEXT,
                sale_price REAL,
                shipping_cost REAL,
                order_status TEXT,
                purchase_date TEXT,
                shipping_address TEXT,
                tracking_number TEXT,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                quantity INTEGER,
                quantity_sold INTEGER,
                status TEXT,
                views INTEGER,
                watchers INTEGER,
                start_date TEXT,
                end_date TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_user TEXT,
                subject TEXT,
                body TEXT,
                item_id TEXT,
                sent_date TEXT,
                replied INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS price_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term TEXT,
                max_price REAL,
                category TEXT,
                active INTEGER DEFAULT 1,
                last_checked TEXT
            );

            CREATE TABLE IF NOT EXISTS sales_stats (
                date TEXT PRIMARY KEY,
                total_sales REAL,
                order_count INTEGER,
                avg_price REAL,
                top_item TEXT
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                details TEXT,
                level TEXT DEFAULT 'INFO'
            );
        """)

        conn.commit()
        conn.close()

    def save_order(self, order: EbayOrder):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            order.order_id, order.item_title, order.buyer_username,
            order.sale_price, order.shipping_cost, order.order_status,
            order.purchase_date, order.shipping_address, order.tracking_number,
            order.last_updated
        ))
        conn.commit()
        conn.close()

    def get_orders(self, status: str = None, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM orders WHERE order_status=? ORDER BY purchase_date DESC LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM orders ORDER BY purchase_date DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_listing(self, listing: EbayListing):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO listings VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            listing.listing_id, listing.title, listing.price,
            listing.quantity, listing.quantity_sold, listing.status,
            listing.views, listing.watchers, listing.start_date, listing.end_date
        ))
        conn.commit()
        conn.close()

    def get_listings(self, status: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM listings WHERE status=? ORDER BY start_date DESC", (status,))
        else:
            cursor.execute("SELECT * FROM listings ORDER BY start_date DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_message(self, msg: EbayMessage):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?)
        """, (
            msg.message_id, msg.from_user, msg.subject, msg.body,
            msg.item_id, msg.sent_date, 1 if msg.replied else 0
        ))
        conn.commit()
        conn.close()

    def get_unread_messages(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE replied=0 ORDER BY sent_date DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def add_price_alert(self, alert: PriceAlert) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_alerts (search_term, max_price, category, active, last_checked)
            VALUES (?,?,?,?,?)
        """, (alert.search_term, alert.max_price, alert.category, 1, alert.last_checked))
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return alert_id

    def get_active_alerts(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM price_alerts WHERE active=1")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_daily_stats(self, date: str, stats: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sales_stats VALUES (?,?,?,?,?)
        """, (date, stats.get('total_sales', 0), stats.get('order_count', 0),
              stats.get('avg_price', 0), stats.get('top_item', '')))
        conn.commit()
        conn.close()

    def get_stats(self, days: int = 7) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM sales_stats WHERE date >= ? ORDER BY date DESC", (since,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def log_activity(self, action: str, details: str, level: str = "INFO"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (timestamp, action, details, level) VALUES (?,?,?,?)
        """, (datetime.now().isoformat(), action, details, level))
        conn.commit()
        conn.close()

# --------------------------------------------------
# eBay API Client
# --------------------------------------------------

class EbayAPIClient:
    """Handles eBay API authentication and requests."""

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.access_token = None
        self.token_expiry = 0

    def _load_config(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {
            "client_id": "",
            "client_secret": "",
            "dev_id": "",
            "redirect_uri": "Siraj_Uddin_b-SirajUdd-ebayma-owxhwcp",
            "ru_name": "Siraj_Uddin_binyasin-SirajUdd-ebayma-owxhwcp",
            "scopes": [
                "https://api.ebay.com/oauth/api_scope",
                "https://api.ebay.com/oauth/api_scope/sell.inventory",
                "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
                "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription"
            ]
        }

    def save_config(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=2)

    def set_credentials(self, client_id: str, client_secret: str):
        self.config["client_id"] = client_id
        self.config["client_secret"] = client_secret
        self.save_config()

    def get_auth_url(self) -> str:
        """Generate eBay OAuth authorization URL for user consent."""
        scopes = "%20".join(self.config["scopes"])
        return (
            f"https://auth.ebay.com/oauth2/authorize"
            f"?client_id={self.config['client_id']}"
            f"&redirect_uri={self.config['redirect_uri']}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&prompt=login"
        )

    def get_access_token(self, authorization_code: str = None) -> Optional[str]:
        """Get OAuth access token."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if authorization_code:
            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.config["redirect_uri"]
            }
        else:
            creds = self.config["client_id"] + ":" + self.config["client_secret"]
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = "Basic " + encoded
            data = {
                "grant_type": "client_credentials",
                "scope": " ".join(self.config["scopes"])
            }

        try:
            resp = requests.post(EBAY_AUTH_URL, headers=headers, data=data, timeout=15)
            if resp.status_code == 200:
                token_data = resp.json()
                self.access_token = token_data["access_token"]
                self.token_expiry = time.time() + token_data.get("expires_in", 7200) - 300
                return self.access_token
            else:
                logger.error(f"Token error: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Token request failed: {e}")
        return None

    def _api_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_orders(self, days: int = 30, limit: int = 50) -> List[Dict]:
        """Fetch recent orders from eBay."""
        token = self.get_access_token()
        if not token:
            logger.error("No access token for orders fetch")
            return []

        try:
            url = f"{EBAY_API_BASE}/sell/fulfillment/v1/order"
            params = {
                "limit": limit,
                "filter": f"creationdate:[{(datetime.now() - timedelta(days=days)).isoformat()}Z..]"
            }
            resp = requests.get(url, headers=self._api_headers(), params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("orders", [])
            else:
                logger.error(f"Orders API error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Orders fetch failed: {e}")
        return []

    def get_inventory_items(self) -> List[Dict]:
        """Fetch all inventory/listing items."""
        token = self.get_access_token()
        if not token:
            return []

        try:
            url = f"{EBAY_API_BASE}/sell/inventory/v1/inventory_item"
            resp = requests.get(url, headers=self._api_headers(), timeout=30)
            if resp.status_code == 200:
                return resp.json().get("inventoryItems", [])
        except Exception as e:
            logger.error(f"Inventory fetch failed: {e}")
        return []

# --------------------------------------------------
# Manager — Core Business Logic
# --------------------------------------------------

class EbayManager:
    """Orchestrates all eBay account operations."""

    def __init__(self):
        self.db = EbayDatabase()
        self.api = EbayAPIClient()

    # ---------- Orders ----------

    def sync_orders(self, days: int = 30) -> int:
        """Fetch orders from eBay API and save to local DB."""
        orders = self.api.get_orders(days=days)
        count = 0
        for o in orders:
            line_items = o.get("lineItems", [{}])
            first_item = line_items[0] if line_items else {}
            shipping = o.get("fulfillmentStartInstructions", [{}])

            ebay_order = EbayOrder(
                order_id=o.get("orderId", ""),
                item_title=first_item.get("title", "Unknown"),
                buyer_username=o.get("buyer", {}).get("username", "Unknown"),
                sale_price=float(o.get("pricingSummary", {}).get("total", {}).get("value", 0)),
                shipping_cost=float(shipping[0].get("shippingCost", {}).get("value", 0)) if shipping else 0,
                order_status=o.get("orderFulfillmentStatus", "PENDING"),
                purchase_date=o.get("creationDate", ""),
                shipping_address=json.dumps(o.get("fulfillmentStartInstructions", [{}])[0].get("shippingStep", {}).get("shipTo", {}) if shipping else {}),
                last_updated=datetime.now().isoformat()
            )
            self.db.save_order(ebay_order)
            count += 1

        self.db.log_activity("sync_orders", f"Synced {count} orders")
        return count

    def get_pending_orders(self) -> List[Dict]:
        """Get orders that need action (not yet shipped)."""
        return self.db.get_orders(status="PENDING")

    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get most recent orders."""
        return self.db.get_orders(limit=limit)

    def add_tracking(self, order_id: str, tracking_number: str):
        """Update tracking number for an order."""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET tracking_number=?, order_status='SHIPPED', last_updated=? WHERE order_id=?",
                       (tracking_number, datetime.now().isoformat(), order_id))
        conn.commit()
        conn.close()
        self.db.log_activity("add_tracking", f"Tracking {tracking_number} added to {order_id}")

    # ---------- Inventory / Listings ----------

    def sync_listings(self) -> int:
        """Sync listings from eBay."""
        items = self.api.get_inventory_items()
        count = 0
        for item in items:
            listing = EbayListing(
                listing_id=item.get("sku", ""),
                title=item.get("product", {}).get("title", "Unknown"),
                price=float(item.get("product", {}).get("aspects", {}).get("Price", [0])[0]),
                quantity=item.get("availability", {}).get("pickupAtLocationAvailability", [{}])[0].get("quantity", 0) if item.get("availability") else 0,
                quantity_sold=0,
                status="active",
                views=0,
                watchers=0,
                start_date=datetime.now().isoformat(),
                end_date=""
            )
            self.db.save_listing(listing)
            count += 1
        self.db.log_activity("sync_listings", f"Synced {count} listings")
        return count

    # ---------- Messages ----------

    def check_messages(self) -> List[Dict]:
        """Get unread buyer messages."""
        return self.db.get_unread_messages()

    # ---------- Price Alerts ----------

    def add_alert(self, search_term: str, max_price: float, category: str = "") -> int:
        alert = PriceAlert(
            alert_id=0,
            search_term=search_term,
            max_price=max_price,
            category=category,
            last_checked=datetime.now().isoformat()
        )
        alert_id = self.db.add_price_alert(alert)
        self.db.log_activity("add_alert", f"Alert '{search_term}' under ${max_price}")
        return alert_id

    def check_alerts(self) -> List[Dict]:
        """Run all active price alerts and return matches."""
        alerts = self.db.get_active_alerts()
        matches = []
        for alert in alerts:
            try:
                url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
                params = {
                    "q": alert["search_term"],
                    "limit": 5,
                    "filter": f"price:[0..{alert['max_price']}],buyingOptions:{{FIXED_PRICE}}"
                }
                token = self.api.get_access_token()
                if token:
                    resp = requests.get(url, headers=self.api._api_headers(), params=params, timeout=15)
                    if resp.status_code == 200:
                        items = resp.json().get("itemSummaries", [])
                        for item in items:
                            matches.append({
                                "alert_id": alert["alert_id"],
                                "search": alert["search_term"],
                                "title": item.get("title"),
                                "price": item.get("price", {}).get("value"),
                                "url": item.get("itemWebUrl"),
                                "image": item.get("image", {}).get("imageUrl")
                            })
                conn = sqlite3.connect(self.db.db_path)
                conn.execute("UPDATE price_alerts SET last_checked=? WHERE alert_id=?",
                            (datetime.now().isoformat(), alert["alert_id"]))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Alert check failed for '{alert['search_term']}': {e}")
        return matches

    # ---------- Reports ----------

    def generate_daily_report(self) -> str:
        """Generate a daily summary report."""
        today = datetime.now().strftime("%Y-%m-%d")
        recent_orders = self.get_recent_orders(limit=20)
        pending = self.get_pending_orders()
        unread_msgs = self.check_messages()
        active_listings = len(self.db.get_listings(status="active"))

        total_sales_today = sum(
            o['sale_price'] for o in recent_orders
            if o['purchase_date'].startswith(today)
        )
        order_count_today = sum(
            1 for o in recent_orders
            if o['purchase_date'].startswith(today)
        )

        self.db.save_daily_stats(today, {
            "total_sales": total_sales_today,
            "order_count": order_count_today,
            "avg_price": total_sales_today / order_count_today if order_count_today else 0,
            "top_item": recent_orders[0]['item_title'] if recent_orders else "N/A"
        })

        report_lines = [
            "=== eBay Account Daily Report ===",
            f"Date: {today}",
            "",
            f"*Orders Today:* {order_count_today}",
            f"*Sales Today:* ${total_sales_today:.2f}",
            "",
            f"*Pending Orders:* {len(pending)}",
            f"*Unread Messages:* {len(unread_msgs)}",
            f"*Active Listings:* {active_listings}",
            "",
            "--- Recent Orders ---"
        ]
        for o in recent_orders[:5]:
            report_lines.append(f"- {o['item_title'][:50]} | ${o['sale_price']:.2f} | {o['order_status']}")

        if pending:
            report_lines.append("")
            report_lines.append("--- Needs Action ---")
            for p in pending[:3]:
                report_lines.append(f"- PENDING: {p['item_title'][:50]} | Ship to: {p['buyer_username']}")

        report = "\n".join(report_lines)
        self.db.log_activity("daily_report", f"Sales: ${total_sales_today:.2f}, Orders: {order_count_today}")
        return report

    def generate_weekly_report(self) -> str:
        """Generate weekly summary report."""
        stats = self.db.get_stats(days=7)
        recent = self.get_recent_orders(limit=50)

        total_sales = sum(s['total_sales'] for s in stats)
        total_orders = sum(s['order_count'] for s in stats)

        report_lines = [
            "=== eBay Account Weekly Report ===",
            f"Period: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"*Total Sales:* ${total_sales:.2f}",
            f"*Total Orders:* {total_orders}",
        ]
        if total_orders:
            report_lines.append(f"*Avg Order Value:* ${total_sales/total_orders:.2f}")
        else:
            report_lines.append("*Avg Order Value:* N/A")

        report_lines.append("")
        report_lines.append("--- Daily Breakdown ---")
        for s in stats:
            report_lines.append(f"- {s['date']}: ${s['total_sales']:.2f} ({s['order_count']} orders)")

        report_lines.append("")
        report_lines.append(f"*Active Listings:* {len(self.db.get_listings(status='active'))}")
        report_lines.append(f"*Unread Messages:* {len(self.check_messages())}")

        report = "\n".join(report_lines)
        self.db.log_activity("weekly_report", f"Sales: ${total_sales:.2f}, Orders: {total_orders}")
        return report

    def get_quick_status(self) -> Dict:
        """Fast snapshot for heartbeat checks."""
        pending = self.get_pending_orders()
        unread = self.check_messages()
        return {
            "pending_orders": len(pending),
            "unread_messages": len(unread),
            "active_listings": len(self.db.get_listings(status="active")),
            "timestamp": datetime.now().isoformat()
        }

# --------------------------------------------------
# CLI Interface
# --------------------------------------------------

def main():
    import sys
    mgr = EbayManager()

    if len(sys.argv) < 2:
        print("Usage: python ebay_manager.py <command> [options]")
        print("Commands: status, orders, listings, alerts, report, setup, sync")
        return

    cmd = sys.argv[1]

    if cmd == "status":
        status = mgr.get_quick_status()
        print(json.dumps(status, indent=2))

    elif cmd == "orders":
        orders = mgr.get_recent_orders(limit=20)
        print(json.dumps(orders, indent=2))

    elif cmd == "report":
        if len(sys.argv) > 2 and sys.argv[2] == "weekly":
            print(mgr.generate_weekly_report())
        else:
            print(mgr.generate_daily_report())

    elif cmd == "alerts":
        alerts = mgr.db.get_active_alerts()
        if len(sys.argv) > 2 and sys.argv[2] == "check":
            matches = mgr.check_alerts()
            print(json.dumps(matches, indent=2))
        else:
            print(json.dumps(alerts, indent=2))

    elif cmd == "add-alert":
        if len(sys.argv) < 4:
            print("Usage: python ebay_manager.py add-alert <search_term> <max_price> [category]")
        else:
            alert_id = mgr.add_alert(sys.argv[2], float(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "")
            print(f"Alert #{alert_id} created")

    elif cmd == "sync":
        orders_count = mgr.sync_orders()
        listings_count = mgr.sync_listings()
        print(json.dumps({"orders_synced": orders_count, "listings_synced": listings_count}))

    elif cmd == "setup":
        print("eBay API Setup")
        print("=" * 40)
        print("1. Go to https://developer.ebay.com/")
        print("2. Create an application in 'My Apps'")
        print("3. Get your App ID (Client ID) and Cert ID (Client Secret)")
        print("4. Run: python ebay_manager.py config <client_id> <client_secret>")

    elif cmd == "config":
        if len(sys.argv) < 4:
            print("Usage: python ebay_manager.py config <client_id> <client_secret>")
        else:
            mgr.api.set_credentials(sys.argv[2], sys.argv[3])
            print("Credentials saved!")
            print(f"Auth URL: {mgr.api.get_auth_url()}")

if __name__ == "__main__":
    main()
