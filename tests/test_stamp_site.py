from tools.stamp_site import stamp_text


def test_stamps_local_modules_and_links():
    src = '''import { A } from "./a.js";
import "../b.js";
const m = await import("../media/mixer.js");
<script type="module" src="js/app.js"></script>
<link rel="stylesheet" href="css/dash.css">
<script src="https://cdn.example.com/x.js"></script>
import { C } from "./c.js?v=old";'''
    out = stamp_text(src, "abc")
    assert 'from "./a.js?v=abc"' in out
    assert 'import "../b.js?v=abc"' in out
    assert 'import("../media/mixer.js?v=abc")' in out
    assert 'src="js/app.js?v=abc"' in out
    assert 'href="css/dash.css?v=abc"' in out
    assert "https://cdn.example.com/x.js\"" in out      # outside links left alone
    assert './c.js?v=old"' in out                       # already stamped left alone
