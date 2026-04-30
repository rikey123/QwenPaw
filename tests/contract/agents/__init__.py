# -*- coding: utf-8 -*-
"""
Agent Contract Tests

Contract tests for agent module interface compliance.

When agent base classes or interfaces change, these tests ensure ALL
agent modules still comply. This prevents "fix one module, break another"
regressions.

Usage:
    from tests.contract.agents import AgentContractTest

    class TestMyAgentContract(AgentContractTest):
        def create_instance(self):
            return MyAgent(...)
"""
