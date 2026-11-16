// Used by build.sh to see which big parts need cutting to fit the bed.
include <lib.scad>
echo(str("SPLIT frame=", frame_split, " plate=", bp_split, " hood=", hood_split));
echo(str("SIZE flange=", fl_w, "x", fl_h, " hood=", hood_out_w, " depth=", frame_D));
echo(str("COUNT frame_bolts=", len(bp_bolts), " hood_bolts=", len([for (p = bp_bolts) if (in_hood_strip(p)) 1])));
