"""LanguagesComponent — language runtime installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    LanguagesPlan,
    expect_plan,
)


class LanguagesComponent(Component):
    label = "languages"
    display_name = "Languages"
    apply_stage = "pre"

    def plan(self, ctx: Context) -> LanguagesPlan:
        from shell_configs.languages import is_language_installed, load_languages

        languages = load_languages()
        missing = [
            l for l in languages if not l.status_only and not is_language_installed(l)
        ]
        status_only = [l for l in languages if l.status_only]
        return LanguagesPlan(
            has_changes=bool(missing),
            all_languages=languages,
            missing=missing,
            status_only=status_only,
        )

    def needs_sudo(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, LanguagesPlan)
        if not plan.missing:
            return False
        from shell_configs.platform import Platform, is_platform

        if not (is_platform(Platform.LINUX) or is_platform(Platform.WSL)):
            return False
        for lang in plan.missing:
            if lang.linux and lang.linux.method == "apt":
                return True
            if not lang.linux and lang.install_cmd and "sudo" in lang.install_cmd:
                return True
        return False

    def display_plan(self, plan: ComponentPlan) -> None:
        plan = expect_plan(plan, LanguagesPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import print_add, print_section

        print_section(self.display_name)
        for lang in plan.missing:
            print_add(f"{lang.name}: {lang.description}", indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, LanguagesPlan)

        from shell_configs.languages import ensure_language_paths

        ensure_language_paths(plan.all_languages)

        if not plan.has_changes:
            return True

        from shell_configs.display import print_error, print_success
        from shell_configs.languages import install_language

        success = True
        for lang in plan.missing:
            ok, msg = install_language(lang, dry_run=ctx.dry_run)
            if ok:
                print_success(msg, indent=2)
            else:
                print_error(msg, indent=2)
                success = False

        ensure_language_paths(plan.all_languages)

        return success

    def status(self, ctx: Context) -> None:
        from shell_configs.display import (
            console,
            print_dim,
            print_success,
            print_warning,
        )
        from shell_configs.languages import get_language_version, is_language_installed

        plan = self.plan(ctx)
        total_managed = len(plan.all_languages) - len(plan.status_only)
        installed_count = total_managed - len(plan.missing)

        if not plan.all_languages:
            print_dim("No languages configured", indent=2)
            console.print()
            return

        if not plan.missing:
            print_success(
                f"{installed_count}/{total_managed} languages installed", indent=2
            )
        else:
            print_warning(
                f"{installed_count}/{total_managed} languages installed "
                f"({len(plan.missing)} missing)",
                indent=2,
            )

        for lang in plan.all_languages:
            if lang.status_only:
                version = get_language_version(lang)
                tag = f" ({version})" if version else ""
                print_dim(f"{lang.name}{tag} [bootstrap prerequisite]", indent=4)
            elif is_language_installed(lang):
                version = get_language_version(lang)
                tag = f" ({version})" if version else ""
                print_success(f"{lang.name}{tag}", indent=4)
            else:
                print_warning(f"{lang.name}: not installed", indent=4)

        console.print()
