OPENQASM 3.0;
include "stdgates.inc";
gate cmod_sub _gate_q_0, _gate_q_1, _gate_q_2 {
  cx _gate_q_0, _gate_q_1;
  ccx _gate_q_0, _gate_q_1, _gate_q_2;
  cx _gate_q_0, _gate_q_1;
  cx _gate_q_0, _gate_q_1;
}
gate cmod_sub_o0 _gate_q_0, _gate_q_1, _gate_q_2 {
  x _gate_q_0;
  cmod_sub _gate_q_0, _gate_q_1, _gate_q_2;
  x _gate_q_0;
}
gate cmod_add _gate_q_0, _gate_q_1, _gate_q_2 {
  ccx _gate_q_0, _gate_q_1, _gate_q_2;
  cx _gate_q_0, _gate_q_1;
}
gate shift _gate_q_0, _gate_q_1, _gate_q_2 {
  cmod_sub_o0 _gate_q_0, _gate_q_1, _gate_q_2;
  cmod_add _gate_q_0, _gate_q_1, _gate_q_2;
}
bit[2] out;
qubit[1] dir;
qubit[2] pos;
out[0] = measure pos[0];
out[1] = measure pos[1];
while (out == 0) {
  h dir[0];
  shift dir[0], pos[0], pos[1];
  out[0] = measure pos[0];
  out[1] = measure pos[1];
}
