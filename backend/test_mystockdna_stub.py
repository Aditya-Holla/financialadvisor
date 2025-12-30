"""Test script for myStockDNA stub service.

Run this with: python test_mystockdna_stub.py
(Ensure you're in the backend directory with venv activated)
"""

import asyncio
from app.services.mystockdna_service import MyStockDNAService
from app.agents.schemas import (
    FinancialState,
    UserIntent,
    UserIntentType,
    Cashflow,
    DebtSummary,
    PortfolioSummary,
)


async def test_invest_proposal():
    """Test INVEST intent proposal generation."""
    print("\n=== Testing INVEST Proposal ===")
    
    service = MyStockDNAService()
    
    # Create test financial state
    financial_state = FinancialState(
        cashflow=Cashflow(monthly_income=5000.0, monthly_expenses=3000.0, net_cashflow=2000.0),
        emergency_fund_months=6.0,
        debt_summary=DebtSummary.default(),
        portfolio_summary=PortfolioSummary.default(),
        goals=[],
        metadata={}
    )
    
    # Create INVEST intent
    user_intent = UserIntent(
        type=UserIntentType.INVEST,
        amount=1000.0,
        risk_change=None,
        target=None,
        timeframe="immediate",
        metadata={}
    )
    
    profile = {"risk_level": "moderate"}
    
    # Generate proposal
    proposal = await service.generate_proposal(financial_state, user_intent, profile)
    
    print(f"✓ Proposal generated successfully")
    print(f"  Target Allocation: {proposal.target_allocation.stocks:.1f}% stocks, "
          f"{proposal.target_allocation.bonds:.1f}% bonds, "
          f"{proposal.target_allocation.cash:.1f}% cash")
    print(f"  Number of trades: {len(proposal.trades)}")
    print(f"  Estimated cost: ${proposal.estimated_cost:.2f}")
    print(f"  Risk delta: {proposal.risk_delta:.2f}")
    print(f"  Reason codes: {proposal.reason_codes}")
    
    # Verify allocation sums to 100%
    total = (proposal.target_allocation.stocks + proposal.target_allocation.bonds + 
             proposal.target_allocation.cash + proposal.target_allocation.other)
    assert abs(total - 100.0) < 0.01, f"Allocation should sum to 100%, got {total}%"
    print(f"✓ Allocation sums to 100% ({total:.2f}%)")
    
    # Verify estimated cost matches intent amount
    assert abs(proposal.estimated_cost - 1000.0) < 0.01, f"Cost should be ~$1000, got ${proposal.estimated_cost}"
    print(f"✓ Estimated cost matches intent amount")
    
    return proposal


async def test_rebalance_proposal():
    """Test REBALANCE intent proposal generation."""
    print("\n=== Testing REBALANCE Proposal ===")
    
    service = MyStockDNAService()
    
    # Create test financial state with existing portfolio
    financial_state = FinancialState(
        cashflow=Cashflow(monthly_income=5000.0, monthly_expenses=3000.0, net_cashflow=2000.0),
        emergency_fund_months=6.0,
        debt_summary=DebtSummary.default(),
        portfolio_summary=PortfolioSummary(
            total_value=50000.0,
            cash_balance=5000.0,
            invested_value=45000.0,
            positions_count=3,
            positions=[]
        ),
        goals=[],
        metadata={}
    )
    
    # Create REBALANCE intent
    user_intent = UserIntent(
        type=UserIntentType.REBALANCE,
        amount=None,
        risk_change=None,
        target=None,
        timeframe="immediate",
        metadata={}
    )
    
    profile = {"risk_level": "moderate"}
    
    # Generate proposal
    proposal = await service.generate_proposal(financial_state, user_intent, profile)
    
    print(f"✓ Proposal generated successfully")
    print(f"  Target Allocation: {proposal.target_allocation.stocks:.1f}% stocks, "
          f"{proposal.target_allocation.bonds:.1f}% bonds, "
          f"{proposal.target_allocation.cash:.1f}% cash")
    print(f"  Number of trades: {len(proposal.trades)}")
    print(f"  Risk delta: {proposal.risk_delta:.2f}")
    print(f"  Reason codes: {proposal.reason_codes}")
    
    # Verify allocation sums to 100%
    total = (proposal.target_allocation.stocks + proposal.target_allocation.bonds + 
             proposal.target_allocation.cash + proposal.target_allocation.other)
    assert abs(total - 100.0) < 0.01, f"Allocation should sum to 100%, got {total}%"
    print(f"✓ Allocation sums to 100% ({total:.2f}%)")
    
    return proposal


async def test_change_risk_proposal():
    """Test CHANGE_RISK intent proposal generation."""
    print("\n=== Testing CHANGE_RISK Proposal ===")
    
    service = MyStockDNAService()
    
    # Create test financial state
    financial_state = FinancialState(
        cashflow=Cashflow(monthly_income=5000.0, monthly_expenses=3000.0, net_cashflow=2000.0),
        emergency_fund_months=6.0,
        debt_summary=DebtSummary.default(),
        portfolio_summary=PortfolioSummary(
            total_value=50000.0,
            cash_balance=5000.0,
            invested_value=45000.0,
            positions_count=3,
            positions=[]
        ),
        goals=[],
        metadata={}
    )
    
    # Create CHANGE_RISK intent (increase risk by 0.1)
    user_intent = UserIntent(
        type=UserIntentType.CHANGE_RISK,
        amount=None,
        risk_change=0.1,  # Increase risk
        target=None,
        timeframe="immediate",
        metadata={}
    )
    
    profile = {"risk_level": "moderate"}
    
    # Generate proposal
    proposal = await service.generate_proposal(financial_state, user_intent, profile)
    
    print(f"✓ Proposal generated successfully")
    print(f"  Target Allocation: {proposal.target_allocation.stocks:.1f}% stocks, "
          f"{proposal.target_allocation.bonds:.1f}% bonds, "
          f"{proposal.target_allocation.cash:.1f}% cash")
    print(f"  Number of trades: {len(proposal.trades)}")
    print(f"  Risk delta: {proposal.risk_delta:.2f}")
    print(f"  Reason codes: {proposal.reason_codes}")
    
    # Verify risk delta matches intent
    assert abs(proposal.risk_delta - 0.1) < 0.01, f"Risk delta should be 0.1, got {proposal.risk_delta}"
    print(f"✓ Risk delta matches intent (0.1)")
    
    # Verify allocation sums to 100%
    total = (proposal.target_allocation.stocks + proposal.target_allocation.bonds + 
             proposal.target_allocation.cash + proposal.target_allocation.other)
    assert abs(total - 100.0) < 0.01, f"Allocation should sum to 100%, got {total}%"
    print(f"✓ Allocation sums to 100% ({total:.2f}%)")
    
    return proposal


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing myStockDNA Stub Service")
    print("=" * 60)
    
    try:
        await test_invest_proposal()
        await test_rebalance_proposal()
        await test_change_risk_proposal()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

