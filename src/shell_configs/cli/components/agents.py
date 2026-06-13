"""AgentsComponent — AI coding agent installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import (
    AgentsPlan,
    Component,
    ComponentPlan,
    Context,
    expect_plan,
)


class AgentsComponent(Component):
    label = "agents"
    display_name = "AI Coding Agents"
    apply_stage = "pre"

    def plan(self, ctx: Context) -> AgentsPlan:
        import shutil

        from shell_configs.agent_manifest import (
            AgentManifest,
            find_orphaned_agents,
            get_default_agent_manifest_path,
        )
        from shell_configs.agents import is_agent_installed, load_agents
        from shell_configs.agents_registry import DEPRECATED_AGENTS

        agents = load_agents()
        missing = [a for a in agents if not is_agent_installed(a)]

        # Check for deprecated agents still installed
        deprecated_installed = []
        for spec in DEPRECATED_AGENTS:
            if shutil.which(spec.command_name):
                if spec.is_still_in_use is not None and spec.is_still_in_use():
                    continue
                deprecated_installed.append(spec)

        # Check for orphaned agents (in manifest but not in YAML)
        manifest = AgentManifest(get_default_agent_manifest_path())
        orphaned = []
        if not manifest.is_new:
            orphaned = find_orphaned_agents(manifest, agents)

        return AgentsPlan(
            has_changes=bool(missing) or bool(deprecated_installed) or bool(orphaned),
            all_agents=agents,
            missing=missing,
            deprecated_installed=deprecated_installed,
            orphaned=orphaned,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        plan = expect_plan(plan, AgentsPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import (
            console,
            print_add,
            print_section,
            print_warning,
        )

        print_section(self.display_name)
        for agent in plan.missing:
            print_add(f"{agent.name}: {agent.description}", indent=2)
        for spec in plan.deprecated_installed:
            print_warning(f"{spec.agent_id}: deprecated, will be removed", indent=2)
        for name in plan.orphaned:
            console.print(f"  {name}: [red]orphaned (source removed)[/red]")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, AgentsPlan)

        if not plan.has_changes:
            return True

        import shutil

        from shell_configs.agent_manifest import (
            AgentManifest,
            get_default_agent_manifest_path,
        )
        from shell_configs.agents import (
            Agent,
            get_agent_install_method,
            install_agent,
            uninstall_agent,
            uninstall_agent_by_manifest_entry,
        )
        from shell_configs.display import print_error, print_success, print_warning

        manifest = AgentManifest(get_default_agent_manifest_path())
        success = True

        # Install missing agents
        for agent in plan.missing:
            ok, msg = install_agent(agent, dry_run=ctx.dry_run)
            if ok:
                print_success(msg, indent=2)
                if not ctx.dry_run:
                    method, package = get_agent_install_method(agent)
                    manifest.record_install(agent.name, agent.command, method, package)
                    manifest.save()
            else:
                print_error(msg, indent=2)
                success = False

        # Remove orphaned agents
        for name in plan.orphaned:
            entry = manifest.agents.get(name)
            if entry:
                ok, msg = uninstall_agent_by_manifest_entry(
                    name,
                    entry.command_name,
                    entry.install_method,
                    entry.package,
                    dry_run=ctx.dry_run,
                )
                if ok:
                    print_success(f"Removed orphaned agent: {name}", indent=2)
                    manifest.remove(name)
                    manifest.save()
                else:
                    print_warning(
                        f"Could not remove orphaned agent {name}: {msg}", indent=2
                    )

        # Remove deprecated agents
        for spec in plan.deprecated_installed:
            if not shutil.which(spec.command_name):
                continue
            dep_agent = Agent(
                name=spec.agent_id,
                command=spec.command_name,
                description="",
            )
            ok, msg = uninstall_agent(dep_agent, dry_run=ctx.dry_run)
            if ok:
                print_success(f"Removed deprecated agent: {spec.agent_id}", indent=2)
            else:
                print_warning(
                    f"Could not remove deprecated agent {spec.agent_id}: {msg}",
                    indent=2,
                )

        return success

    def status(self, ctx: Context) -> None:
        from shell_configs.agents import get_agent_version, is_agent_installed
        from shell_configs.display import (
            console,
            print_dim,
            print_success,
            print_warning,
        )

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

        # Warn about deprecated agents
        for spec in plan.deprecated_installed:
            print_warning(
                f"{spec.agent_id}: installed but deprecated "
                "— will be removed on next install",
                indent=4,
            )

        # Warn about orphaned agents
        if plan.orphaned:
            print_warning(
                f"{len(plan.orphaned)} orphaned agent(s) "
                "— run 'shell-configs install' to clean up",
                indent=2,
            )

        console.print()

    def uninstall(self, ctx: Context) -> None:
        import shutil

        from shell_configs.agent_manifest import (
            AgentManifest,
            get_default_agent_manifest_path,
        )
        from shell_configs.agents import (
            Agent,
            uninstall_agent,
            uninstall_agent_by_manifest_entry,
        )
        from shell_configs.agents_registry import DEPRECATED_AGENTS
        from shell_configs.display import print_operation_result, print_warning
        from shell_configs.manager import OperationResult

        # Remove manifest-tracked agents
        manifest = AgentManifest(get_default_agent_manifest_path())
        if manifest.agents:
            for name in list(manifest.agents.keys()):
                entry = manifest.agents[name]
                ok, msg = uninstall_agent_by_manifest_entry(
                    name,
                    entry.command_name,
                    entry.install_method,
                    entry.package,
                )
                if ok:
                    print_operation_result(OperationResult.REMOVED, msg)
                    manifest.remove(name)
                    manifest.save()
                else:
                    print_warning(msg)

        # Remove deprecated agents
        for spec in DEPRECATED_AGENTS:
            if not shutil.which(spec.command_name):
                continue
            agent = Agent(
                name=spec.agent_id,
                command=spec.command_name,
                description="",
            )
            ok, msg = uninstall_agent(agent)
            if ok:
                print_operation_result(OperationResult.REMOVED, msg)
            else:
                print_warning(msg)
