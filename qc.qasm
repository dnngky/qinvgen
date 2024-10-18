OPENQASM 3.0;
include "stdgates.inc";
bit[2] c;
qubit[2] q;
while (!c[0]) {
  x q[0];
  c[0] = measure q[0];
}
if (c[1]) {
  h q[1];
  c[1] = measure q[1];
}
c[1] = measure q[1];
