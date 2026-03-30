"""plans.py — Subscription plans and pricing configuration.

exports: PLANS, get_user_plan, get_plan_details, calculate_credits_from_amount
used_by: credits.py, stripe.py, billing.py router
rules:   must define clear credit limits and pricing; must support plan upgrades/downgrades
agent:   DataEngineer | 2024-01-15 | created comprehensive plan definitions with credit rules
         message: "implement plan proration and upgrade/downgrade logic"
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from agenthub.db.models import User

# Plan definitions
PLANS = {
    "free": {
        "name": "Free",
        "description": "Basic plan for getting started",
        "monthly_price": 0.00,
        "annual_price": 0.00,
        "currency": "USD",
        "credit_cap": 100,  # Maximum credits user can have
        "credits_per_month": 10,  # Monthly credit allowance
        "max_agents": 3,
        "max_scheduled_tasks": 5,
        "max_team_members": 1,
        "support_level": "community",
        "features": [
            "Basic AI agents",
            "Limited credits",
            "Community support",
            "Basic analytics"
        ],
        "credit_expiry_days": 30,  # Credits expire after 30 days
        "concurrent_runs": 1,
        "api_access": False,
        "custom_domains": False,
        "sla": None,
    },
    "starter": {
        "name": "Starter",
        "description": "For individuals and small teams",
        "monthly_price": 29.00,
        "annual_price": 290.00,  # ~20% discount
        "currency": "USD",
        "credit_cap": 1000,
        "credits_per_month": 100,
        "max_agents": 10,
        "max_scheduled_tasks": 20,
        "max_team_members": 3,
        "support_level": "email",
        "features": [
            "All Free features",
            "More credits",
            "Email support",
            "Advanced analytics",
            "Scheduled tasks",
            "Basic API access"
        ],
        "credit_expiry_days": 60,
        "concurrent_runs": 3,
        "api_access": True,
        "custom_domains": False,
        "sla": "99.5%",
    },
    "pro": {
        "name": "Pro",
        "description": "For professional teams and businesses",
        "monthly_price": 99.00,
        "annual_price": 950.00,  # ~20% discount
        "currency": "USD",
        "credit_cap": 5000,
        "credits_per_month": 500,
        "max_agents": 50,
        "max_scheduled_tasks": 100,
        "max_team_members": 10,
        "support_level": "priority",
        "features": [
            "All Starter features",
            "Priority support",
            "Advanced API access",
            "Custom domains",
            "Team collaboration",
            "Advanced security"
        ],
        "credit_expiry_days": 90,
        "concurrent_runs": 10,
        "api_access": True,
        "custom_domains": True,
        "sla": "99.9%",
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "For large organizations with custom needs",
        "monthly_price": None,  # Custom pricing
        "annual_price": None,
        "currency": "USD",
        "credit_cap": None,  # Unlimited
        "credits_per_month": None,  # Custom
        "max_agents": None,  # Unlimited
        "max_scheduled_tasks": None,
        "max_team_members": None,
        "support_level": "dedicated",
        "features": [
            "All Pro features",
            "Dedicated support",
            "Custom integrations",
            "On-premise deployment",
            "Custom SLA",
            "Security audit",
            "Training & onboarding"
        ],
        "credit_expiry_days": 365,
        "concurrent_runs": 50,
        "api_access": True,
        "custom_domains": True,
        "sla": "99.99%",
    }
}

# Credit pricing tiers (for one-time purchases)
CREDIT_PRICING_TIERS = [
    {"credits": 100, "price": 10.00, "price_per_credit": 0.10},
    {"credits": 500, "price": 45.00, "price_per_credit": 0.09},
    {"credits": 1000, "price": 80.00, "price_per_credit": 0.08},
    {"credits": 5000, "price": 350.00, "price_per_credit": 0.07},
    {"credits": 10000, "price": 600.00, "price_per_credit": 0.06},
]

# Supported currencies and exchange rates (simplified)
CURRENCY_RATES = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.35,
    "AUD": 1.52,
    "JPY": 148.50,
}


class PlanManager:
    """Manage subscription plans and pricing."""
    
    @staticmethod
    def get_user_plan(db: Session, user_id: int) -> str:
        """Get user's current plan.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Plan name (e.g., "free", "starter", "pro", "enterprise")
        """
        # In production, you would have a user_plans table
        # For now, we'll use a simplified approach
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return "free"
        
        # Check if user is superuser (gets enterprise features)
        if user.is_superuser:
            return "enterprise"
        
        # Default to free plan
        # In production, you would check subscription status
        return "free"
    
    @staticmethod
    def get_plan_details(plan_name: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific plan.
        
        Args:
            plan_name: Plan name
            
        Returns:
            Plan details or None if not found
        """
        plan = PLANS.get(plan_name.lower())
        if not plan:
            return None
        
        # Add calculated fields
        plan_copy = plan.copy()
        
        # Calculate annual savings
        if plan_copy["monthly_price"] and plan_copy["annual_price"]:
            monthly_total = plan_copy["monthly_price"] * 12
            annual_price = plan_copy["annual_price"]
            if annual_price < monthly_total:
                plan_copy["annual_savings"] = monthly_total - annual_price
                plan_copy["annual_savings_percent"] = round(
                    (1 - annual_price / monthly_total) * 100, 1
                )
            else:
                plan_copy["annual_savings"] = 0
                plan_copy["annual_savings_percent"] = 0
        
        return plan_copy
    
    @staticmethod
    def calculate_credits_from_amount(
        amount: float,
        currency: str = "USD",
        plan: Optional[str] = None
    ) -> Tuple[float, float]:
        """Calculate credits from payment amount.
        
        Args:
            amount: Payment amount
            currency: Currency code
            plan: Optional plan for bonus credits
            
        Returns:
            Tuple of (credits, effective_price_per_credit)
        """
        # Convert to USD if needed
        if currency != "USD":
            rate = CURRENCY_RATES.get(currency.upper(), 1.0)
            amount_usd = amount / rate
        else:
            amount_usd = amount
        
        # Find best pricing tier
        best_tier = None
        for tier in sorted(CREDIT_PRICING_TIERS, key=lambda x: x["price_per_credit"]):
            if amount_usd >= tier["price"]:
                best_tier = tier
        
        if not best_tier:
            # Use smallest tier ratio
            smallest_tier = min(CREDIT_PRICING_TIERS, key=lambda x: x["price_per_credit"])
            credits = amount_usd / smallest_tier["price_per_credit"]
            price_per_credit = smallest_tier["price_per_credit"]
        else:
            # Calculate based on best tier
            base_credits = best_tier["credits"]
            remaining_amount = amount_usd - best_tier["price"]
            
            if remaining_amount > 0:
                # Add remaining amount at tier's price per credit
                additional_credits = remaining_amount / best_tier["price_per_credit"]
                credits = base_credits + additional_credits
            else:
                credits = base_credits
            
            price_per_credit = best_tier["price_per_credit"]
        
        # Apply plan bonus if applicable
        if plan and plan != "free":
            plan_config = PLANS.get(plan)
            if plan_config:
                # Give bonus credits for subscription plans
                bonus_multiplier = {
                    "starter": 1.1,  # 10% bonus
                    "pro": 1.2,      # 20% bonus
                    "enterprise": 1.3,  # 30% bonus
                }.get(plan, 1.0)
                
                credits *= bonus_multiplier
        
        return round(credits, 2), price_per_credit
    
    @staticmethod
    def get_credit_pricing_tiers(currency: str = "USD") -> list:
        """Get credit pricing tiers in specified currency.
        
        Args:
            currency: Currency code
            
        Returns:
            List of pricing tiers
        """
        rate = CURRENCY_RATES.get(currency.upper(), 1.0)
        
        tiers = []
        for tier in CREDIT_PRICING_TIERS:
            tier_copy = tier.copy()
            tier_copy["price"] = round(tier["price"] * rate, 2)
            tier_copy["currency"] = currency
            tiers.append(tier_copy)
        
        return tiers
    
    @staticmethod
    def can_user_create_agent(db: Session, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user can create a new agent based on their plan.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (can_create, error_message)
        """
        plan = PlanManager.get_user_plan(db, user_id)
        plan_config = PLANS.get(plan)
        
        if not plan_config:
            return False, "Invalid plan"
        
        # Get user's current agent count
        from agenthub.db.models import Agent
        agent_count = db.query(Agent).filter(Agent.owner_id == user_id).count()
        
        max_agents = plan_config.get("max_agents")
        if max_agents is not None and agent_count >= max_agents:
            return False, f"Plan limit reached. Maximum {max_agents} agents allowed."
        
        return True, None
    
    @staticmethod
    def can_user_run_concurrently(db: Session, user_id: int, current_runs: int) -> Tuple[bool, Optional[str]]:
        """Check if user can run more agents concurrently.
        
        Args:
            db: Database session
            user_id: User ID
            current_runs: Number of currently running agents
            
        Returns:
            Tuple of (can_run, error_message)
        """
        plan = PlanManager.get_user_plan(db, user_id)
        plan_config = PLANS.get(plan)
        
        if not plan_config:
            return False, "Invalid plan"
        
        max_concurrent = plan_config.get("concurrent_runs", 1)
        if current_runs >= max_concurrent:
            return False, f"Concurrent run limit reached. Maximum {max_concurrent} concurrent runs allowed."
        
        return True, None
    
    @staticmethod
    def get_plan_upgrade_options(current_plan: str) -> list:
        """Get available upgrade options from current plan.
        
        Args:
            current_plan: Current plan name
            
        Returns:
            List of upgrade options
        """
        plan_order = ["free", "starter", "pro", "enterprise"]
        
        try:
            current_index = plan_order.index(current_plan)
            upgrade_options = []
            
            for i in range(current_index + 1, len(plan_order)):
                plan_name = plan_order[i]
                plan_config = PLANS.get(plan_name)
                if plan_config:
                    upgrade_options.append({
                        "plan": plan_name,
                        "name": plan_config["name"],
                        "description": plan_config["description"],
                        "monthly_price": plan_config["monthly_price"],
                        "annual_price": plan_config["annual_price"],
                        "features": plan_config["features"],
                    })
            
            return upgrade_options
        except ValueError:
            return []
    
    @staticmethod
    def calculate_prorated_amount(
        current_plan: str,
        new_plan: str,
        days_remaining: int,
        billing_cycle_days: int = 30
    ) -> Tuple[Optional[float], Optional[str]]:
        """Calculate prorated amount for plan change.
        
        Args:
            current_plan: Current plan name
            new_plan: New plan name
            days_remaining: Days remaining in current billing cycle
            billing_cycle_days: Total days in billing cycle
            
        Returns:
            Tuple of (prorated_amount, error_message)
        """
        current_config = PLANS.get(current_plan)
        new_config = PLANS.get(new_plan)
        
        if not current_config or not new_config:
            return None, "Invalid plan"
        
        current_monthly = current_config.get("monthly_price")
        new_monthly = new_config.get("monthly_price")
        
        if current_monthly is None or new_monthly is None:
            return None, "Plan does not support monthly billing"
        
        # Calculate daily rates
        current_daily = current_monthly / billing_cycle_days
        new_daily = new_monthly / billing_cycle_days
        
        # Calculate credit for unused portion of current plan
        credit_amount = current_daily * days_remaining
        
        # Calculate charge for new plan for remaining days
        charge_amount = new_daily * days_remaining
        
        # Prorated amount (could be positive or negative)
        prorated_amount = charge_amount - credit_amount
        
        return round(prorated_amount, 2), None


# Convenience functions
def get_user_plan(db: Session, user_id: int) -> str:
    """Get user's current plan."""
    return PlanManager.get_user_plan(db, user_id)


def get_plan_details(plan_name: str) -> Optional[Dict[str, Any]]:
    """Get details for a specific plan."""
    return PlanManager.get_plan_details(plan_name)


def calculate_credits_from_amount(
    amount: float,
    currency: str = "USD",
    plan: Optional[str] = None
) -> Tuple[float, float]:
    """Calculate credits from payment amount."""
    return PlanManager.calculate_credits_from_amount(amount, currency, plan)