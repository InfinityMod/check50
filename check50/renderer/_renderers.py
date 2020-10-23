import json
import pathlib

import jinja2
import pkg_resources
import termcolor

from junit_xml import TestSuite, TestCase

TEMPLATES = pathlib.Path(pkg_resources.resource_filename("check50.renderer", "templates"))


def to_html(slug, results, version):
    with open(TEMPLATES / "results.html") as f:
        content = f.read()

    template = jinja2.Template(
        content, autoescape=jinja2.select_autoescape(enabled_extensions=("html",)))
    html = template.render(slug=slug, results=results, version=version)

    return html


def to_json(slug, results, version):
    return json.dumps({"slug": slug, "results": results, "version": version}, indent=4)


def to_ansi(slug, results, version, _log=False):
    lines = [termcolor.colored(_("Results for {} generated by check50 v{}").format(slug, version), "white", attrs=["bold"])]
    for result in results:
        if result["passed"]:
            lines.append(termcolor.colored(f":) {result['description']}", "green"))
        elif result["passed"] is None:
            lines.append(termcolor.colored(f":| {result['description']}", "yellow"))
            lines.append(termcolor.colored(f"    {result['cause'].get('rationale') or _('check skipped')}", "yellow"))
            if result["cause"].get("error") is not None:
                lines.append(f"    {result['cause']['error']['type']}: {result['cause']['error']['value']}")
                lines += (f"    {line.rstrip()}" for line in result["cause"]["error"]["traceback"])
        else:
            lines.append(termcolor.colored(f":( {result['description']}", "red"))
            if result["cause"].get("rationale") is not None:
                lines.append(termcolor.colored(f"    {result['cause']['rationale']}", "red"))
            if result["cause"].get("help") is not None:
                lines.append(termcolor.colored(f"    {result['cause']['help']}", "red"))

        if _log:
            lines += (f"    {line}" for line in result["log"])
    return "\n".join(lines)

def to_junitXML(slug, results, version):
    cases = []
    for r in results:
        name = r["name"]
        log = "\n".join(r["log"])
        cause = r["cause"]
        tc = TestCase(name, classname=f"check50.{slug}.{name}", log=log, allow_multiple_subelements=True)
        if r["passed"] == False:
            tc.add_error_info(message="error", output=cause["rationale"])
            if cause.get("help", None) is not None:
                tc.add_error_info(message="help", output=cause["help"])
        elif r["passed"] is None:
            tc.add_skipped_info(message="reason", output=cause["rationale"])
            if cause.get("help", None) is not None:
                tc.add_skipped_info(message="help", output=cause["help"])
        cases.append(tc)

    ts = TestSuite(f"check50.{slug}", cases)
    # pretty printing is on by default but can be disabled using prettyprint=False
    return TestSuite.to_xml_string([ts])