"""AgentsComponent — AI coding agent installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import AgentsPlan, Component, ComponentPlan, Context


class AgentsComponent(Component):
    label = "agents"
    display_name = "AI Coding Agents"

    def plan(self, ctx: Context) -> AgentsPlan:
        from shell_configs.agents import is_agent_installed, load_agents

        agents = load_agents()
        missing = [a for a in agents if not is_agent_installed(a)]
        return AgentsPlan(
            has_changes=bool(missing),
            all_agents=agents,
            missing=missing,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, AgentsPlan):
            raise TypeError(f"expected AgentsPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import print_add, print_section

        print_section(self.display_name)
        for agent in plan.missing:
            print_add(f"{agent.name}: {agent.description}", indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, AgentsPlan):
            raise TypeError(f"expected AgentsPlan, got {type(plan).__name__}")

        if not plan.has_changes:
            return True

        from shell_configs.agents import install_agent
        from shell_configs.display import print_error, print_success

        success = True
        for agent in plan.missing:
            ok, msg = install_agent(agent, dry_run=ctx.dry_run)
            if ok:
                print_success(msg, indent=2)
            else:
                print_error(msg, indent=2)
                success = False
        return success

    def status(self, ctx: Context) -> None:
        from shell_configs.agents import get_agent_version, is_agent_installed
        from shell_configs.display import print_dim, print_success, print_warning

        plan = self.plan(ctx)
        total = len(plan.all_agents)
        installed_count = total - len(plan.missing)

        if not plan.all_agents:
            print_dim("No agents configured", indent=2)
            return

        if not plan.missing:
            print_success(f"{installed_count}/{total} agents installed", indent=2)
        else:
            print_warning(
                f"{installed_count}/{total} agents installed "
                f"({len(plan.missing)} missing)",
                indent=2,
            )

        for agent in plan.all_agents:
            if is_agent_installed(agent):
                version = get_agent_version(agent)
                tag = f" ({version})" if version else ""
                print_success(f"{agent.name}{tag}", indent=4)
            else:
                print_warning(f"{agent.name}: not installed", indent=4)
