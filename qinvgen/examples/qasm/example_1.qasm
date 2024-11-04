OPENQASM 3.0;
include "stdgates.inc";
bit[1] c;
int switch_dummy;
qubit[3] q;
qubit[1] r;
h q[0];
h q[1];
h q[2];
c[0] = measure q[0];
switch_dummy = c;
switch (switch_dummy) {
  case 0 {
    cx q[2], r[0];
  }
  case 1 {
    reset q[0];
    reset q[1];
  }
}
while (c == 1) {
  h q[0];
  cx q[0], q[2];
  c[0] = measure q[2];
}
