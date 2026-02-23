"""SIR Epidemiological Model adapted for financial contagion."""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SIRParameters:
    """Parameters for the financial SIR model."""
    beta: float = 0.3        # Infection rate (risk propagation speed)
    gamma: float = 0.1       # Recovery rate (risk dissipation speed)
    delta: float = 0.05      # Mortality rate (permanent damage probability)
    vaccination: float = 0.0  # Immunity rate (hedging effectiveness)


@dataclass
class SIRState:
    """State of a node in the SIR model."""
    susceptible: float  # Fraction of portfolio at risk
    infected: float     # Fraction experiencing contagion
    recovered: float    # Fraction recovered (resilient)
    dead: float         # Fraction permanently impaired


class FinancialSIRModel:
    """SIR model adapted for financial contagion simulation.

    Maps epidemiological concepts to financial risk:
    - S (Susceptible): Assets/entities not yet affected but exposed
    - I (Infected): Assets/entities experiencing risk contagion
    - R (Recovered): Assets/entities that have weathered the shock
    - D (Dead): Assets/entities permanently impaired (default/failure)

    The R0 (basic reproduction number) in finance represents the average
    number of counterparties that one distressed entity will spread risk to.
    """

    def __init__(self, params: Optional[SIRParameters] = None):
        self.params = params or SIRParameters()

    def compute_r0(self) -> float:
        """Compute the basic reproduction number R0.

        R0 > 1 means contagion will spread exponentially.
        R0 < 1 means contagion will die out.
        """
        effective_gamma = self.params.gamma + self.params.delta
        if effective_gamma == 0:
            return float("inf")
        return self.params.beta / effective_gamma

    def simulate(
        self,
        initial_infected: float = 0.01,
        steps: int = 100,
        population: int = 1000,
    ) -> list[SIRState]:
        """Run SIR simulation and return state trajectory."""
        S = 1.0 - initial_infected
        I = initial_infected
        R = 0.0
        D = 0.0

        trajectory = [SIRState(S, I, R, D)]

        for _ in range(steps):
            new_infected = self.params.beta * S * I
            new_recovered = self.params.gamma * I
            new_dead = self.params.delta * I
            new_vaccinated = self.params.vaccination * S

            S = S - new_infected - new_vaccinated
            I = I + new_infected - new_recovered - new_dead
            R = R + new_recovered + new_vaccinated
            D = D + new_dead

            # Clamp values
            S = max(0, min(1, S))
            I = max(0, min(1, I))
            R = max(0, min(1, R))
            D = max(0, min(1, D))

            trajectory.append(SIRState(S, I, R, D))

            # Stop if infection dies out
            if I < 0.001:
                break

        return trajectory

    def compute_contagion_risk_metrics(
        self,
        trajectory: list[SIRState],
    ) -> dict:
        """Compute key risk metrics from a simulation trajectory."""
        peak_infected = max(s.infected for s in trajectory)
        peak_step = next(
            i for i, s in enumerate(trajectory) if s.infected == peak_infected
        )
        total_affected = trajectory[-1].recovered + trajectory[-1].dead
        mortality_rate = trajectory[-1].dead / total_affected if total_affected > 0 else 0

        return {
            "r0": round(self.compute_r0(), 2),
            "peak_infection_rate": round(peak_infected * 100, 1),
            "peak_step": peak_step,
            "total_affected_pct": round(total_affected * 100, 1),
            "mortality_rate_pct": round(mortality_rate * 100, 1),
            "contagion_contained": self.compute_r0() < 1.0,
            "risk_level": self._classify_risk(peak_infected, total_affected),
        }

    def _classify_risk(self, peak_infected: float, total_affected: float) -> str:
        """Classify overall contagion risk level."""
        if peak_infected > 0.5 or total_affected > 0.7:
            return "critical"
        elif peak_infected > 0.3 or total_affected > 0.5:
            return "high"
        elif peak_infected > 0.15 or total_affected > 0.3:
            return "elevated"
        elif peak_infected > 0.05:
            return "moderate"
        else:
            return "low"

    def calibrate_from_market_data(
        self,
        correlation_matrix: np.ndarray,
        volatilities: np.ndarray,
    ) -> SIRParameters:
        """Calibrate SIR parameters from market data.

        - Beta (infection rate) ~ average correlation * volatility
        - Gamma (recovery rate) ~ inverse of average recovery time
        - Delta (mortality) ~ tail risk measure
        """
        avg_correlation = np.mean(np.abs(correlation_matrix[np.triu_indices_from(
            correlation_matrix, k=1
        )]))
        avg_volatility = np.mean(volatilities)

        beta = float(avg_correlation * avg_volatility * 10)  # Scale factor
        gamma = max(0.05, 1.0 / (avg_volatility * 20))  # Higher vol → slower recovery
        delta = float(avg_volatility * 0.1)  # Tail risk proxy

        self.params = SIRParameters(
            beta=min(beta, 0.9),
            gamma=min(gamma, 0.5),
            delta=min(delta, 0.2),
        )
        return self.params
