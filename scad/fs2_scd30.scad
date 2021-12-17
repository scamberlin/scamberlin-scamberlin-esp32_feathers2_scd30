include<esp32-common.scad>;

/*
// fit testing
translate([0,0,23])
rotate([0,180,180])
import("aqi-monitor-basic-cover.stl");
*/

// width and height of board
W=102;
H=68;

// how much the whole board layout is offset from origin
TX=16;
TY=-23;

difference() {
    union() {
            cube_center([W,H,1.5]);
        difference() {
            cube_center([W,H,3]);
            cube_center([W-3,H-3, 6]);
            
        }
        for(s=[-1,1]) for(t=[-1,1])
            translate([s*(W-8)/2,t*(H-8)/2])
            cube_center([8,8,15]);
    }
    for(s=[-1,1]) for(t=[-1,1]) {
        translate([s*(W-8)/2,t*(H-8)/2]) {
            cylinder(d=6,h=3.5,$fn=32);
            cylinder(d=3.3,h=50,$fn=32);
        }
    }
}

translate([TX,TY,1.5]) {
    translate([31,4,0]) usbport();
    
    translate([0,4,0])
    feathers2();
    
    translate([0,40,0])
    feathers2();
    
    translate([-45,23,0])
    rotate([0,0,90])
    feathers2_display();
    

}
