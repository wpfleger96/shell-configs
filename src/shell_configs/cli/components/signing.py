"""SigningComponent — SSH key lifecycle setup and status."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    SigningPlan,
    expect_plan,
)


class SigningComponent(Component):
    label = "signing"
    display_name = "SSH Key Lifecycle"
    apply_stage = "post"

    def plan(self, ctx: Context) -> SigningPlan:
        from shell_configs.bootstrap import is_command_available

        if not is_command_available("gh"):
            return SigningPlan(has_changes=True, gh_available=False)

        from shell_configs.signing import setup_signing

        results = setup_signing(auto_fix=False, interactive=False)
        failed = [r for r in results if not r.success and not r.skipped]
        return SigningPlan(has_changes=bool(failed), results=results, failed=failed)

    def display_plan(self, plan: ComponentPlan) -> None:
        plan = expect_plan(plan, SigningPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import (
            print_dim,
            print_section,
            print_warning,
        )

        print_section(self.display_name)

        if not plan.gh_available:
            print_dim(
                "gh not installed — signing validation will run after packages are installed",
                indent=2,
            )
            return

        for r in plan.failed:
            print_warning(r.message, indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, SigningPlan)
        if not plan.has_changes:
            return True

        from shell_configs.signing import setup_signing

        results = setup_signing(auto_fix=True, interactive=False)
        return all(r.success or r.skipped for r in results)

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console, print_success, print_warning
        from shell_configs.signing import setup_signing

        signing_results = setup_signing(auto_fix=False, interactive=False)
        for r in signing_results:
            if r.success:
                print_success(r.message, indent=2)
            else:
                print_warning(r.message, indent=2)

        console.print()
