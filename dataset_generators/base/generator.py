"""
Base data generator with shared dimension generation logic.
"""

from __future__ import annotations

import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from .utils import set_random_seed


@dataclass
class GeneratorConfig:
    """Configuration for dataset generators."""

    seed: int = 42
    n_products: int = 150
    n_customers: int = 500
    n_stores: int = 80
    n_promotions: int = 50
    n_transactions: int = 50000
    start_date: str = "2023-01-01"
    end_date: str = "2025-12-31"
    output_dir: str | None = None


class BaseDataGenerator(ABC):
    """
    Abstract base class for dataset generators.

    Provides shared dimension generation logic for both clean (star schema)
    and dirty (super table) generators.
    """

    def __init__(self, config: GeneratorConfig) -> None:
        """
        Initialize the generator with configuration.

        Args:
            config: Generator configuration settings
        """
        self.config = config
        set_random_seed(config.seed)

    def _generate_dim_date(self) -> pd.DataFrame:
        """
        Generate a date dimension with fiscal calendar support.
        Fiscal year starts February 1st (common for beverage companies).
        """
        dates = pd.date_range(start=self.config.start_date, end=self.config.end_date, freq="D")

        records = []
        for d in dates:
            # Fiscal year starts Feb 1
            if d.month >= 2:
                fiscal_year = d.year
            else:
                fiscal_year = d.year - 1

            # Fiscal quarter (Feb-Apr=Q1, May-Jul=Q2, Aug-Oct=Q3, Nov-Jan=Q4)
            fiscal_month = (d.month - 2) % 12 + 1
            fiscal_quarter = (fiscal_month - 1) // 3 + 1

            records.append(
                {
                    "date_key": int(d.strftime("%Y%m%d")),
                    "full_date": d.date(),
                    "year": d.year,
                    "month": d.month,
                    "month_name": d.strftime("%B"),
                    "day_of_month": d.day,
                    "day_of_week": d.dayofweek + 1,  # 1=Monday, 7=Sunday
                    "day_name": d.strftime("%A"),
                    "week_of_year": d.isocalendar()[1],
                    "quarter": (d.month - 1) // 3 + 1,
                    "fiscal_year": fiscal_year,
                    "fiscal_quarter": fiscal_quarter,
                    "fiscal_quarter_name": f"FY{fiscal_year} Q{fiscal_quarter}",
                    "is_weekend": d.dayofweek >= 5,
                    "is_holiday": d.month == 12 and d.day == 25,  # Simplified
                }
            )

        return pd.DataFrame(records)

    def _generate_dim_product(self) -> pd.DataFrame:
        """
        Generate product dimension with category hierarchy.
        """
        categories = {
            "Beer": {
                "subcategories": ["Lager", "Ale", "IPA", "Stout", "Pilsner"],
                "brands": ["Northern Brew", "Mountain Gold", "Craft Select", "Heritage Lager"],
            },
            "Cider": {"subcategories": ["Apple", "Pear", "Mixed Fruit"], "brands": ["Orchard Fresh", "Valley Cider"]},
            "Ready-to-Drink": {
                "subcategories": ["Vodka Soda", "Rum Punch", "Tequila Mix"],
                "brands": ["Social Hour", "Party Starter"],
            },
            "Non-Alcoholic": {
                "subcategories": ["NA Beer", "Sparkling Water", "Energy Drink"],
                "brands": ["Zero Proof", "Pure Fizz", "Boost"],
            },
        }

        pack_sizes = ["Single", "6-Pack", "12-Pack", "24-Pack", "Keg"]
        container_types = ["Can", "Bottle", "Draft"]

        records = []
        product_id = 1000

        for category, details in categories.items():
            for subcategory in details["subcategories"]:
                for brand in details["brands"]:
                    for _ in range(random.randint(2, 5)):
                        pack_size = random.choice(pack_sizes)
                        container = random.choice(container_types)

                        # Skip illogical combinations
                        if pack_size == "Keg" and container != "Draft":
                            continue

                        unit_volume_ml = random.choice([355, 473, 500, 650])

                        records.append(
                            {
                                "product_key": product_id,
                                "product_sku": f"SKU-{product_id}",
                                "product_name": f"{brand} {subcategory} {pack_size}",
                                "brand": brand,
                                "category": category,
                                "subcategory": subcategory,
                                "pack_size": pack_size,
                                "container_type": container,
                                "unit_volume_ml": unit_volume_ml,
                                "units_per_pack": {"Single": 1, "6-Pack": 6, "12-Pack": 12, "24-Pack": 24, "Keg": 1}[
                                    pack_size
                                ],
                                "alcohol_percentage": 0.0
                                if category == "Non-Alcoholic"
                                else round(random.uniform(4.0, 8.5), 1),
                                "unit_cost": round(random.uniform(0.80, 3.50), 2),
                                "unit_price": round(random.uniform(1.50, 6.00), 2),
                                "is_seasonal": random.random() < 0.15,
                                "launch_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))).date(),
                                "is_active": random.random() < 0.92,
                            }
                        )
                        product_id += 1

                        if len(records) >= self.config.n_products:
                            break
                    if len(records) >= self.config.n_products:
                        break
                if len(records) >= self.config.n_products:
                    break
            if len(records) >= self.config.n_products:
                break

        return pd.DataFrame(records[: self.config.n_products])

    def _generate_dim_customer(self) -> pd.DataFrame:
        """
        Generate customer dimension with segments.
        """
        segments = ["Enterprise", "Mid-Market", "Small Business", "Independent"]
        channels = ["On-Premise", "Off-Premise", "E-Commerce"]
        customer_types = ["Bar/Restaurant", "Liquor Store", "Grocery", "Convenience Store", "Hotel", "Stadium/Venue"]

        regions = {
            "Northeast": ["New York", "Boston", "Philadelphia"],
            "Southeast": ["Miami", "Atlanta", "Charlotte"],
            "Midwest": ["Chicago", "Detroit", "Minneapolis"],
            "Southwest": ["Dallas", "Houston", "Phoenix"],
            "West": ["Los Angeles", "San Francisco", "Seattle"],
        }

        records = []
        for i in range(1, self.config.n_customers + 1):
            region = random.choice(list(regions.keys()))
            city = random.choice(regions[region])
            segment = random.choices(segments, weights=[0.1, 0.2, 0.35, 0.35])[0]

            records.append(
                {
                    "customer_key": i,
                    "customer_id": f"CUST-{i:05d}",
                    "customer_name": f"{random.choice(['The', 'Big', 'Golden', 'Silver', 'Royal', 'Corner'])} {random.choice(['Oak', 'Pine', 'Eagle', 'Lion', 'Star', 'Moon'])} {random.choice(customer_types).split('/')[0]}",
                    "customer_type": random.choice(customer_types),
                    "segment": segment,
                    "channel": random.choice(channels),
                    "city": city,
                    "region": region,
                    "credit_limit": random.choice([5000, 10000, 25000, 50000, 100000]),
                    "payment_terms_days": random.choice([15, 30, 45, 60]),
                    "account_manager": f"Rep-{random.randint(1, 20):02d}",
                    "customer_since": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2000))).date(),
                    "is_active": random.random() < 0.88,
                }
            )

        return pd.DataFrame(records)

    def _generate_dim_store(self) -> pd.DataFrame:
        """
        Generate store/distribution center dimension.
        """
        store_types = ["Distribution Center", "Regional Warehouse", "Local Depot"]

        records = []
        for i in range(1, self.config.n_stores + 1):
            records.append(
                {
                    "store_key": i,
                    "store_code": f"DC-{i:03d}",
                    "store_name": f"{random.choice(['North', 'South', 'East', 'West', 'Central'])} {random.choice(['Metro', 'Valley', 'Heights', 'Industrial'])} Facility",
                    "store_type": random.choice(store_types),
                    "state": random.choice(["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]),
                    "square_footage": random.randint(10000, 100000),
                    "max_capacity_pallets": random.randint(500, 5000),
                    "has_cold_storage": random.random() < 0.7,
                    "open_date": (datetime(2015, 1, 1) + timedelta(days=random.randint(0, 3000))).date(),
                }
            )

        return pd.DataFrame(records)

    def _generate_dim_promotion(self) -> pd.DataFrame:
        """
        Generate promotion dimension.
        """
        promo_types = ["Price Discount", "Buy One Get One", "Bundle Deal", "Loyalty Reward", "Seasonal Special"]

        records = []
        for i in range(1, self.config.n_promotions + 1):
            start_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))
            duration = random.randint(7, 60)

            records.append(
                {
                    "promotion_key": i,
                    "promotion_code": f"PROMO-{i:03d}",
                    "promotion_name": f"{random.choice(['Summer', 'Winter', 'Spring', 'Fall', 'Holiday', 'Weekend'])} {random.choice(['Blast', 'Savings', 'Special', 'Deal', 'Bonanza'])}",
                    "promotion_type": random.choice(promo_types),
                    "discount_percentage": random.choice([5, 10, 15, 20, 25, 30]),
                    "start_date": start_date.date(),
                    "end_date": (start_date + timedelta(days=duration)).date(),
                    "minimum_quantity": random.choice([0, 6, 12, 24]),
                    "is_stackable": random.random() < 0.3,
                }
            )

        return pd.DataFrame(records)

    def _generate_fact_sales(
        self,
        dim_date: pd.DataFrame,
        dim_product: pd.DataFrame,
        dim_customer: pd.DataFrame,
        dim_store: pd.DataFrame,
        dim_promotion: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Generate fact table with sales transactions.
        """
        date_keys = dim_date["date_key"].tolist()
        product_keys = dim_product["product_key"].tolist()
        customer_keys = dim_customer["customer_key"].tolist()
        store_keys = dim_store["store_key"].tolist()
        promotion_keys = [None] + dim_promotion["promotion_key"].tolist()  # None = no promotion

        # Create product lookup for pricing
        product_prices = dim_product.set_index("product_key")[["unit_cost", "unit_price", "units_per_pack"]].to_dict(
            "index"
        )

        records = []
        for i in range(1, self.config.n_transactions + 1):
            product_key = random.choice(product_keys)
            product_info = product_prices[product_key]

            quantity = random.choices([1, 2, 3, 6, 12, 24, 48], weights=[0.3, 0.25, 0.15, 0.1, 0.1, 0.07, 0.03])[0]
            unit_price = product_info["unit_price"]
            unit_cost = product_info["unit_cost"]

            # Apply promotion discount
            promo_key = random.choices(promotion_keys, weights=[0.7] + [0.3 / len(dim_promotion)] * len(dim_promotion))[
                0
            ]
            discount_pct = 0
            if promo_key:
                promo = dim_promotion[dim_promotion["promotion_key"] == promo_key].iloc[0]
                discount_pct = promo["discount_percentage"] / 100

            gross_amount = quantity * unit_price
            discount_amount = gross_amount * discount_pct
            net_amount = gross_amount - discount_amount
            cost_amount = quantity * unit_cost

            records.append(
                {
                    "sale_key": i,
                    "date_key": random.choice(date_keys),
                    "product_key": product_key,
                    "customer_key": random.choice(customer_keys),
                    "store_key": random.choice(store_keys),
                    "promotion_key": promo_key,
                    "quantity_sold": quantity,
                    "unit_price": unit_price,
                    "gross_amount": round(gross_amount, 2),
                    "discount_amount": round(discount_amount, 2),
                    "net_amount": round(net_amount, 2),
                    "cost_amount": round(cost_amount, 2),
                    "profit_amount": round(net_amount - cost_amount, 2),
                    "units_sold": quantity * product_info["units_per_pack"],
                }
            )

        return pd.DataFrame(records)

    @abstractmethod
    def generate(self) -> dict[str, pd.DataFrame]:
        """
        Generate the complete dataset.

        Returns:
            Dictionary mapping table names to DataFrames
        """
        pass

    def save_to_parquet(self, datasets: dict[str, pd.DataFrame], output_dir: str) -> None:
        """
        Save generated datasets to parquet files.

        Args:
            datasets: Dictionary mapping table names to DataFrames
            output_dir: Directory to save parquet files
        """
        os.makedirs(output_dir, exist_ok=True)
        for name, df in datasets.items():
            path = os.path.join(output_dir, f"{name}.parquet")
            df.to_parquet(path, index=False)
            print(f"  Saved {path} ({len(df):,} rows)")

    def print_summary(self, datasets: dict[str, pd.DataFrame], title: str) -> None:
        """
        Print a summary of generated datasets.

        Args:
            datasets: Dictionary mapping table names to DataFrames
            title: Title for the summary output
        """
        print(f"\n{title}:")
        for name, df in datasets.items():
            print(f"  {name}: {len(df):,} rows, {len(df.columns)} columns")
