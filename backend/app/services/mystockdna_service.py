"""myStockDNA service for generating portfolio proposals.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

This service generates PortfolioProposal objects using stub/dummy logic.
The actual myStockDNA model is not yet implemented, but the architecture
is ready for integration when the model is available.
"""

from typing import Optional, Dict, Any, List
from app.agents.schemas import (
    FinancialState,
    UserIntent,
    UserIntentType,
    PortfolioProposal,
    AssetAllocation,
    Trade,
)
from app.models.errors import ExternalServiceError


class MyStockDNAService:
    """
    Service for generating portfolio proposals using myStockDNA model.
    
    For MVP, this uses intelligent stub logic to generate realistic proposals.
    The actual myStockDNA model integration will replace the stub logic later.
    
    Responsibilities:
    - Generate portfolio proposals (allocations, rebalance suggestions, trade lists)
    - Operate independently of user interaction
    - Return structured PortfolioProposal objects
    - Consider FinancialState and UserIntent when generating proposals
    """
    
    # Default allocation templates
    CONSERVATIVE_ALLOCATION = AssetAllocation(stocks=40.0, bonds=50.0, cash=10.0, other=0.0)
    MODERATE_ALLOCATION = AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0)
    AGGRESSIVE_ALLOCATION = AssetAllocation(stocks=80.0, bonds=10.0, cash=10.0, other=0.0)
    
    # ETF symbols for diversification
    STOCK_ETFS = ["SPY", "VTI", "QQQ"]  # Broad market, total market, tech
    BOND_ETFS = ["BND", "AGG", "TLT"]   # Total bond, aggregate bond, treasury
    CASH_EQUIVALENTS = ["SHV", "BIL"]    # Short-term treasury, treasury bills
    
    def __init__(self):
        """Initialize myStockDNA service."""
        pass
    
    async def generate_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> PortfolioProposal:
        """
        Generate a portfolio proposal based on financial state and user intent.
        
        Args:
            financial_state: User's current financial state
            user_intent: User's intent or request
            profile: User profile data
            
        Returns:
            PortfolioProposal with target allocation, trades, and metadata
            
        Raises:
            ExternalServiceError: If proposal generation fails
        """
        try:
            # Route to appropriate proposal generator based on intent type
            if user_intent.type == UserIntentType.INVEST:
                return await self._generate_invest_proposal(financial_state, user_intent, profile)
            elif user_intent.type == UserIntentType.REBALANCE:
                return await self._generate_rebalance_proposal(financial_state, user_intent, profile)
            elif user_intent.type == UserIntentType.WITHDRAW:
                return await self._generate_withdraw_proposal(financial_state, user_intent, profile)
            elif user_intent.type == UserIntentType.CHANGE_RISK:
                return await self._generate_change_risk_proposal(financial_state, user_intent, profile)
            else:
                # Default to invest if intent type is unknown
                return await self._generate_invest_proposal(financial_state, user_intent, profile)
        except Exception as e:
            raise ExternalServiceError(
                f"myStockDNA proposal generation failed: {str(e)}",
                "MYSTOCKDNA_PROPOSAL_ERROR"
            )
    
    async def _generate_invest_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> PortfolioProposal:
        """Generate proposal for investing new money."""
        # Get investment amount (default to $1000 if not specified)
        amount = user_intent.amount or 1000.0
        
        # Determine target allocation based on risk preference or default to moderate
        risk_level = profile.get("risk_level", "moderate")
        if risk_level == "conservative":
            target_allocation = self.CONSERVATIVE_ALLOCATION
        elif risk_level == "aggressive":
            target_allocation = self.AGGRESSIVE_ALLOCATION
        else:
            target_allocation = self.MODERATE_ALLOCATION
        
        # Adjust allocation if risk_change is specified
        if user_intent.risk_change is not None:
            target_allocation = self._adjust_allocation_for_risk(
                target_allocation,
                user_intent.risk_change
            )
        
        # Generate trades to achieve target allocation
        trades = self._generate_trades_for_allocation(
            amount=amount,
            target_allocation=target_allocation,
            current_allocation=None  # New investment, no current allocation
        )
        
        # Calculate risk delta (0.0 for new investment, unless risk_change specified)
        risk_delta = user_intent.risk_change or 0.0
        
        return PortfolioProposal(
            target_allocation=target_allocation,
            trades=trades,
            reason_codes=["STUB_PROPOSAL", "INVEST", f"AMOUNT_{amount:.0f}"],
            risk_delta=risk_delta,
            estimated_cost=amount,
            metadata={
                "intent_type": user_intent.type.value,
                "investment_amount": amount,
                "is_stub": True
            }
        )
    
    async def _generate_rebalance_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> PortfolioProposal:
        """Generate proposal for rebalancing existing portfolio."""
        # Calculate current allocation from portfolio
        current_allocation = self._calculate_current_allocation(financial_state)
        
        # Determine target allocation
        risk_level = profile.get("risk_level", "moderate")
        if risk_level == "conservative":
            target_allocation = self.CONSERVATIVE_ALLOCATION
        elif risk_level == "aggressive":
            target_allocation = self.AGGRESSIVE_ALLOCATION
        else:
            target_allocation = self.MODERATE_ALLOCATION
        
        # Adjust if risk_change specified
        if user_intent.risk_change is not None:
            target_allocation = self._adjust_allocation_for_risk(
                target_allocation,
                user_intent.risk_change
            )
        
        # Calculate rebalance trades
        portfolio_value = financial_state.portfolio_summary.total_value
        trades = self._generate_rebalance_trades(
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            portfolio_value=portfolio_value
        )
        
        # Calculate risk delta from allocation change
        risk_delta = (target_allocation.stocks - current_allocation.stocks) / 100.0
        
        # Estimate cost (could be negative if selling more than buying)
        estimated_cost = sum(trade.estimated_total or 0.0 for trade in trades if trade.action == "BUY")
        estimated_cost -= sum(trade.estimated_total or 0.0 for trade in trades if trade.action == "SELL")
        
        return PortfolioProposal(
            target_allocation=target_allocation,
            trades=trades,
            reason_codes=["STUB_PROPOSAL", "REBALANCE"],
            risk_delta=risk_delta,
            estimated_cost=estimated_cost,
            metadata={
                "intent_type": user_intent.type.value,
                "current_allocation": {
                    "stocks": current_allocation.stocks,
                    "bonds": current_allocation.bonds,
                    "cash": current_allocation.cash
                },
                "is_stub": True
            }
        )
    
    async def _generate_withdraw_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> PortfolioProposal:
        """Generate proposal for withdrawing money."""
        # Get withdrawal amount
        amount = user_intent.amount or 1000.0
        
        # Calculate current allocation
        current_allocation = self._calculate_current_allocation(financial_state)
        
        # Generate sell trades to meet withdrawal amount
        # Prefer selling from stocks first (more liquid), then bonds, then cash
        trades = []
        remaining_amount = amount
        
        # Sell from stocks if needed
        if remaining_amount > 0 and current_allocation.stocks > 0:
            portfolio_value = financial_state.portfolio_summary.total_value
            stock_value = portfolio_value * (current_allocation.stocks / 100.0)
            sell_amount = min(remaining_amount, stock_value)
            
            if sell_amount > 0:
                # Use first stock ETF
                trades.append(Trade(
                    symbol=self.STOCK_ETFS[0],
                    action="SELL",
                    quantity=1,  # Placeholder - would calculate actual shares
                    estimated_price=sell_amount,
                    estimated_total=sell_amount
                ))
                remaining_amount -= sell_amount
        
        # Sell from bonds if still needed
        if remaining_amount > 0 and current_allocation.bonds > 0:
            portfolio_value = financial_state.portfolio_summary.total_value
            bond_value = portfolio_value * (current_allocation.bonds / 100.0)
            sell_amount = min(remaining_amount, bond_value)
            
            if sell_amount > 0:
                trades.append(Trade(
                    symbol=self.BOND_ETFS[0],
                    action="SELL",
                    quantity=1,
                    estimated_price=sell_amount,
                    estimated_total=sell_amount
                ))
                remaining_amount -= sell_amount
        
        # Use cash if still needed
        if remaining_amount > 0:
            # Cash withdrawal doesn't need a trade, but we'll note it
            pass
        
        # Target allocation stays the same (or adjusts slightly)
        target_allocation = current_allocation
        
        return PortfolioProposal(
            target_allocation=target_allocation,
            trades=trades,
            reason_codes=["STUB_PROPOSAL", "WITHDRAW", f"AMOUNT_{amount:.0f}"],
            risk_delta=0.0,  # Withdrawal doesn't change risk profile
            estimated_cost=-amount,  # Negative cost (money coming out)
            metadata={
                "intent_type": user_intent.type.value,
                "withdrawal_amount": amount,
                "is_stub": True
            }
        )
    
    async def _generate_change_risk_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> PortfolioProposal:
        """Generate proposal for changing risk profile."""
        # Calculate current allocation
        current_allocation = self._calculate_current_allocation(financial_state)
        
        # Adjust allocation based on risk_change
        # risk_change > 0 means more risk (more stocks), < 0 means less risk (more bonds)
        risk_change = user_intent.risk_change or 0.0
        
        target_allocation = self._adjust_allocation_for_risk(
            current_allocation,
            risk_change
        )
        
        # Generate rebalance trades
        portfolio_value = financial_state.portfolio_summary.total_value
        trades = self._generate_rebalance_trades(
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            portfolio_value=portfolio_value
        )
        
        # Risk delta is the change amount
        risk_delta = risk_change
        
        # Estimate cost
        estimated_cost = sum(trade.estimated_total or 0.0 for trade in trades if trade.action == "BUY")
        estimated_cost -= sum(trade.estimated_total or 0.0 for trade in trades if trade.action == "SELL")
        
        return PortfolioProposal(
            target_allocation=target_allocation,
            trades=trades,
            reason_codes=["STUB_PROPOSAL", "CHANGE_RISK", f"DELTA_{risk_change:.2f}"],
            risk_delta=risk_delta,
            estimated_cost=estimated_cost,
            metadata={
                "intent_type": user_intent.type.value,
                "risk_change": risk_change,
                "is_stub": True
            }
        )
    
    def _calculate_current_allocation(
        self,
        financial_state: FinancialState
    ) -> AssetAllocation:
        """Calculate current allocation from portfolio summary."""
        portfolio_value = financial_state.portfolio_summary.total_value
        
        if portfolio_value == 0:
            # No portfolio, return default
            return AssetAllocation(stocks=0.0, bonds=0.0, cash=100.0, other=0.0)
        
        cash_balance = financial_state.portfolio_summary.cash_balance
        invested_value = financial_state.portfolio_summary.invested_value
        
        # For stub, assume invested value is all stocks (simplified)
        # In real implementation, would analyze positions to determine stock/bond split
        stocks_pct = (invested_value / portfolio_value) * 100.0
        cash_pct = (cash_balance / portfolio_value) * 100.0
        bonds_pct = 0.0  # Simplified - would analyze positions in real implementation
        other_pct = 0.0
        
        # Normalize to sum to 100%
        total = stocks_pct + bonds_pct + cash_pct + other_pct
        if total > 0:
            stocks_pct = (stocks_pct / total) * 100.0
            bonds_pct = (bonds_pct / total) * 100.0
            cash_pct = (cash_pct / total) * 100.0
        else:
            stocks_pct = 0.0
            bonds_pct = 0.0
            cash_pct = 100.0
        
        return AssetAllocation(
            stocks=stocks_pct,
            bonds=bonds_pct,
            cash=cash_pct,
            other=other_pct
        )
    
    def _adjust_allocation_for_risk(
        self,
        base_allocation: AssetAllocation,
        risk_change: float
    ) -> AssetAllocation:
        """
        Adjust allocation based on risk change.
        
        Args:
            base_allocation: Base allocation to adjust
            risk_change: Risk change (-1.0 to 1.0), positive = more risk
            
        Returns:
            Adjusted AssetAllocation (normalized to sum to 100%)
        """
        # Clamp risk_change to reasonable range
        risk_change = max(-1.0, min(1.0, risk_change))
        
        # Calculate adjustment: risk_change * 20% max shift
        # e.g., risk_change=0.1 means shift 2% from bonds to stocks
        shift_pct = risk_change * 20.0
        
        # Limit shift to available bonds (can't shift more than we have)
        # Also limit shift to available room in stocks (can't exceed 100%)
        max_shift_from_bonds = base_allocation.bonds
        max_shift_to_stocks = 100.0 - base_allocation.stocks - base_allocation.cash - base_allocation.other
        actual_shift = min(abs(shift_pct), max_shift_from_bonds, max_shift_to_stocks)
        
        # Apply shift in correct direction
        if shift_pct > 0:
            new_stocks = base_allocation.stocks + actual_shift
            new_bonds = base_allocation.bonds - actual_shift
        else:
            new_stocks = base_allocation.stocks - actual_shift
            new_bonds = base_allocation.bonds + actual_shift
        
        # Ensure non-negative and within bounds
        new_stocks = max(0.0, min(100.0, new_stocks))
        new_bonds = max(0.0, min(100.0, new_bonds))
        
        # Keep cash and other the same
        new_allocation = AssetAllocation(
            stocks=new_stocks,
            bonds=new_bonds,
            cash=base_allocation.cash,
            other=base_allocation.other
        )
        
        # Normalize to ensure it sums to exactly 100%
        total = new_stocks + new_bonds + base_allocation.cash + base_allocation.other
        if abs(total - 100.0) > 0.01:  # Only normalize if significantly off
            scale = 100.0 / total
            new_stocks = new_stocks * scale
            new_bonds = new_bonds * scale
            new_cash = base_allocation.cash * scale
            new_other = base_allocation.other * scale
            
            return AssetAllocation(
                stocks=new_stocks,
                bonds=new_bonds,
                cash=new_cash,
                other=new_other
            )
        
        return new_allocation
    
    def _generate_trades_for_allocation(
        self,
        amount: float,
        target_allocation: AssetAllocation,
        current_allocation: Optional[AssetAllocation]
    ) -> List[Trade]:
        """Generate trades to achieve target allocation for new investment."""
        trades = []
        
        # Calculate amounts for each asset class
        stock_amount = amount * (target_allocation.stocks / 100.0)
        bond_amount = amount * (target_allocation.bonds / 100.0)
        # Cash doesn't need a trade
        
        # Generate stock trades
        if stock_amount > 0:
            # Split across multiple ETFs for diversification
            num_stock_etfs = min(len(self.STOCK_ETFS), 2)  # Use up to 2 stock ETFs
            per_etf = stock_amount / num_stock_etfs
            
            for i in range(num_stock_etfs):
                trades.append(Trade(
                    symbol=self.STOCK_ETFS[i],
                    action="BUY",
                    quantity=1,  # Placeholder - would calculate actual shares
                    estimated_price=per_etf,
                    estimated_total=per_etf
                ))
        
        # Generate bond trades
        if bond_amount > 0:
            trades.append(Trade(
                symbol=self.BOND_ETFS[0],
                action="BUY",
                quantity=1,
                estimated_price=bond_amount,
                estimated_total=bond_amount
            ))
        
        return trades
    
    def _generate_rebalance_trades(
        self,
        current_allocation: AssetAllocation,
        target_allocation: AssetAllocation,
        portfolio_value: float
    ) -> List[Trade]:
        """Generate trades to rebalance from current to target allocation."""
        trades = []
        
        # Calculate target values
        target_stocks_value = portfolio_value * (target_allocation.stocks / 100.0)
        target_bonds_value = portfolio_value * (target_allocation.bonds / 100.0)
        target_cash_value = portfolio_value * (target_allocation.cash / 100.0)
        
        # Calculate current values
        current_stocks_value = portfolio_value * (current_allocation.stocks / 100.0)
        current_bonds_value = portfolio_value * (current_allocation.bonds / 100.0)
        current_cash_value = portfolio_value * (current_allocation.cash / 100.0)
        
        # Calculate differences
        stock_diff = target_stocks_value - current_stocks_value
        bond_diff = target_bonds_value - current_bonds_value
        
        # Generate stock trades
        if abs(stock_diff) > 10.0:  # Only trade if difference is significant (>$10)
            if stock_diff > 0:
                # Buy stocks
                trades.append(Trade(
                    symbol=self.STOCK_ETFS[0],
                    action="BUY",
                    quantity=1,
                    estimated_price=stock_diff,
                    estimated_total=stock_diff
                ))
            else:
                # Sell stocks
                trades.append(Trade(
                    symbol=self.STOCK_ETFS[0],
                    action="SELL",
                    quantity=1,
                    estimated_price=abs(stock_diff),
                    estimated_total=abs(stock_diff)
                ))
        
        # Generate bond trades
        if abs(bond_diff) > 10.0:  # Only trade if difference is significant
            if bond_diff > 0:
                # Buy bonds
                trades.append(Trade(
                    symbol=self.BOND_ETFS[0],
                    action="BUY",
                    quantity=1,
                    estimated_price=bond_diff,
                    estimated_total=bond_diff
                ))
            else:
                # Sell bonds
                trades.append(Trade(
                    symbol=self.BOND_ETFS[0],
                    action="SELL",
                    quantity=1,
                    estimated_price=abs(bond_diff),
                    estimated_total=abs(bond_diff)
                ))
        
        return trades

