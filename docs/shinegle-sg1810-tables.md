# SG1810 programmer: parameter and fault tables

Made by `python -m teryx shinegle-manual` from
[`config/shinegle-sg1810-params.yaml`](../config/shinegle-sg1810-params.yaml) and
[`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml). Edit those, not this file.
The rest of the manual (how to use the programmer, our notes) is in
[`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md).

Copied from the manual's own tables, typos kept. **CN ours** is our own translation
of the Chinese, to check Shinegle's English against. Values are "for reference only"
(the manual's words) and won't match every controller.

## Attached list 1: programmer parameters (附表1 编程器参数)

**Green** = highlighted green in the manual, the only ones Shinegle say can be changed.

| Page | Name | Value | Chinese | CN ours | Shinegle English | Remark (Chinese) | Remark CN ours | Remark (English) | Our note |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **F_Spd** (green) | 8000-13800 | 最大前进速度系数 | Max forward speed coefficient | Coefficient for Max.forward speed | 已最优，无需调整，乘 0.5 为设定的最大速度 F_Spd :8000~16000 | Already optimal, no need to adjust. x 0.5 = the set top speed. F_Spd: 8000-16000 | Optimized,no change, Max.speed=0.5*F_Spd | Value column says 8000-13800 but the remark says 8000-16000. The English drops the range. Highlighted green (adjustable) even though the remark says no need to adjust. |
| 0 | F_Spd2 | 5000 | 最大前进速度 2 系数 | Max forward speed 2 coefficient | Coefficient for Max.forward speed2 | 特殊车辆用，乘 0.5 为设定速度 | For special vehicles. x 0.5 = the set speed | For special vechicle, Max.speed=0.5*F_Spd2 |  |
| 0 | **R_Spd** (green) | 6144 | 最大后退速度系数 | Max reverse speed coefficient | Coefficient for Max.backward speed | 可适当调整，乘 0.5 为设定的最大速度 R_Spd: 6000~10000 | Can be adjusted to suit. x 0.5 = the set top speed. R_Spd: 6000-10000 | R_Spd: 6000~10000 Max.speed=0.5*R_Spd | The English leaves out "can be adjusted to suit". The Fig. 3 photo shows R_Spd 3500 (below the 6000 bottom of the range), F_Spd 8300 and Kf 300, so real units differ from the table. |
| 0 | Kf |  | 系统参数 | System parameter | system parameter | 内部数据，禁止修改 | Internal data, do not change | Internal data, Prohibition of modification | No value printed. |
| 1 | R_Trat2 | 24 | 后退电流 2 响应系数 | Reverse current 2 response coefficient | Respond coefficient for backward current 2 | 特殊车辆用 | For special vehicles | For special vechicle |  |
| 1 | B_Trat2 | 24 | 制动电流 2 响应系数 | Braking current 2 response coefficient | Respond coefficient for break current 2 | 特殊车辆用 | For special vehicles | For special vechicle | 制动 means braking. Shinegle's English writes "break" for "brake" throughout. |
| 1 | F_Trat | 64 | 前进电流响应系数 | Forward current response coefficient | Respond coefficient for forward current | 已优化 , F_Trat: 24~72 | Already optimised. F_Trat: 24-72 | optimized , F_Trat: 24~72 |  |
| 1 | R_Trat | 24 | 后退电流响应系数 | Reverse current response coefficient | Respond coefficient for backward current | 已优化 R_Trat: 24~64 | Already optimised. R_Trat: 24-64 | optimized, R_Trat: 24~64 |  |
| 2 | B_Trat | 32 | 制动电流响应系数 | Braking current response coefficient | Respond coefficient for break current 2 | 已优化 B_Trat: 24~64 | Already optimised. B_Trat: 24-64 | optimized, B_Trat: 24~64 | The Chinese is the plain braking current response. The English wrongly adds "2" (that's B_Trat2 on page 1). |
| 2 | F_Trat3 | 32 | 前进电流 3 响应系数 | Forward current 3 response coefficient | Respond coefficient for forward current 3 | 特殊车辆用 | For special vehicles | For special vechicle |  |
| 2 | Neut_K | 32 | 预留 | Reserved | reserved | 预留 | Reserved | Rreserved |  |
| 2 | B_Trat3 | 24 | 后退电流 3 响应系数 | Reverse current 3 response coefficient | Respond coefficient for backward current3 | 特殊车辆用 | For special vehicles | For special vechicle | The name starts B_ (brake) but both languages say reverse (后退) current 3. Name or description is wrong in the manual. |
| 3 | F_Rat2 | 10 | 前进加速率 2 | Forward acceleration rate 2 | ramp-up rate for forward | 特殊车辆用 | For special vehicles | For special vechicle |  |
| 3 | R_Rat2 | 18 | 后退加速率 2 | Reverse acceleration rate 2 | ramp-up rate for | 特殊车辆用 | For special vehicles | For special vechicle | The English is cut short in the manual ("ramp-up rate for"). |
| 3 | DecRat2 | 10 | 减速率 2 | Deceleration rate 2 | deceleration rate for backward 2 | 特殊车辆用 | For special vehicles | For special vechicle | The Chinese just says deceleration rate 2. The English adds "for backward", which isn't in the Chinese. |
| 3 | BrkRat2 | 24 | 制动速率 2 | Braking rate 2 | break rate 2 | 特殊车辆用 | For special vehicles | For special vechicle |  |
| 4 | **F_Rat** (green) | 18 | 前进加速率 | Forward acceleration rate | ramp-up rate for forward | 可修改，F_Rat: 3~36 | Can be changed. F_Rat: 3-36 | Modifiable, F_Rat: 3-36 |  |
| 4 | **R_Rat** (green) | 12 | 后退加速率 | Reverse acceleration rate | ramp-up rate for backward | 可修改，R_Rat: 3~36 | Can be changed. R_Rat: 3-36 | Modifiable, R_Rat: 3-36 |  |
| 4 | **DecRat** (green) | 12 | 减速率 | Deceleration rate | deceleration | 可修改，DecRat: 3~36 | Can be changed. DecRat: 3-36 | Modifiable, DecRat: 3-36 |  |
| 4 | **B_Rat** (green) | 12 | 制动速率 | Braking rate | break rate | 可修改，B_Rat: 3~36 | Can be changed. B_Rat: 3-36 | Modifiable, B_Rat: 3-36 |  |
| 5 | EmrgK | 24 | 预留 | Reserved | reserved | 预留 | Reserved | Reserved |  |
| 5 | IncRat3 | 18 | 加速率 3 | Acceleration rate 3 | ramp-up rate 3 | 特殊车辆用 | For special vehicles | For special vechicle |  |
| 5 | F_Rat2 | 18 | 加速率 2 | Acceleration rate 2 | ramp-up rate forward speed 3 | 特殊车辆用 | For special vehicles | For special vechicle | Same name as F_Rat2 on page 3 (value 10 there, 18 here). The Chinese says rate 2, the English says "forward speed 3". Check on the handheld which one it really shows. |
| 5 | Pls_Mt | 32/48/64 | 电机脉冲 | Motor pulses (speed sensor pulses per rev) | motor pulse | 严禁修改 | Strictly do not change | prohibited to change without authorized |  |
| 6 | Func | 224 | 系统特殊功能 | System special function | special function | 系统参数 | System parameter | System parameter, prohibited to change without authorized |  |
| 6 | ConstT | 200 | 预留 | Reserved | reserved |  |  | Reserved,ConstT: 20~1500 |  |
| 6 | TorqM |  | 预留 | Reserved | reserved |  |  | prohibited to modify | No value printed. |
| 6 | Bvolt | 24~144 | 电池电压 | Battery voltage | battery voltage | 预设好 | Preset | preset value, prohibited to change without authorized |  |
| 7 | Func2 | 0/2 | 系统特殊功能 2 | System special function 2 | special function 2 | 系统参数 | System parameter | system parameter, prohibited to modify |  |
| 7 | NC | 0/2 | 预留 | Reserved | reserved | 系统参数 | System parameter | System parameter |  |
| 7 | K1 | 6144 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change |  |
| 7 | K2 | 480 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| 8 | K3 | 590 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| 8 | K4 | 4096 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| 8 | K5 | 480 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| 8 | K6 | 650 | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| 9 | B_Cur | 512-4096 | 刹车系数 | Brake coefficient | For Coefficient brake |  |  | Prohibited to change without authorized. Regenerative brake Coefficient | Only the English remark says "regenerative". No Chinese remark printed. |
| 9 | Slope |  | 预留 | Reserved | reserved. Stop Voltgage Coefficient | 预留 | Reserved | Prohibited to change without authorized | No value printed. The English "Stop Voltgage Coefficient" has no Chinese match. |
| 9 | EmgSpd | 378 | 预留 | Reserved | reserved | 预留 | Reserved | Reserved |  |
| 9 | EmgTm | 141 | 预留 | Reserved | reserved | 预留 | Reserved | Reserved |  |
| a | KF0 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| a | KF1 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| a | KF2 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| a | KF3 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to unauthorized modify |  |
| b | KD5 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change |  |
| b | KD4 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| b | KD3 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to unauthorized modify |  |
| b | KD2 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| c | KD1 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| c | KD0 |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change |  |
| c | BrkTm | 20000 | 预留 | Reserved | reserved. Different controller type different meaning | 关断延时，已优化 | Switch-off delay, already optimised | delay time to turn off(ms) BrkTm: 5000-20000 |  |
| c | OffTm | 0 | 预留 | Reserved | reserved | 预留 | Reserved | Reserved |  |
| d | PedSet | 50 | 油门初始值 | Throttle starting value (offset) | offset value of peddal | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| d | CDMax |  | 预留 | Reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | system parameter, prohibited to change without authorized | No value printed. |
| d | F_Trat2 | 24 | 前进电流 2 响应系数 | Forward current 2 response coefficient | respond coefficient for forward current 2 | 特殊车辆用 | For special vehicles | For special vehicle |  |
| d | TypDia | 52 | 轮胎参数，预留 | Tyre parameter, reserved | Tire Parameter. Just for controller inside | 系统参数 | System parameter | system parameter, prohibited to change without authorized |  |
| e | Ra_X10 | 100 | 差速器参数，预留 | Differential (final drive) parameter, reserved | Reduction Ratio Parameter. Just for controller inside | 系统参数 | System parameter | system parameter, prohibited to change without authorized | Name suggests the ratio x 10, so 100 = 10:1. Not stated in the manual. |
| e | V3Set | 10240 | 系统预留 | System reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| e | T3Set | 5120 | 系统预留 | System reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| e | V1Set | 8192 | 系统预留 | System reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| f | T1Set | 5120 | 系统预留 | System reserved | reserved | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| f | Soff3 |  | 系统预留 | System reserved | reserved. For the future | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |
| f | Soff1 |  | 系统预留 | System reserved | reserved. For the future | 严禁擅自修改 | Strictly do not change without permission | prohibited to change without authorized |  |

**Footnote (备注):**

> 正常情况下，出厂的控制器均经过优化，性能达到最佳，第 0 页和 4 页的绿色标注的参数可以根据车辆的载重量进行适当修改，以获得最佳的客户体验和舒适度。
>
> CN ours: Normally every controller is optimised at the factory for best performance. The green parameters on pages 0 and 4 can be adjusted to suit the vehicle's load, for the best experience and comfort.
>
> Note: The default value(different controller has different default value) of controller is optimized and the peformance is the best normally, if you really want to adjust some value of parameter, please just adjust those parameters which is labeled green according to your electric vehicle with our permission in order to get the best user-experience. We don't suggest you to modify them without permission.

Our note: The English adds "with our permission" and "different controller has different default value". The Chinese just says the green ones can be adjusted for load.

## Attached list 2: fault codes (附表2 SHINEGLE 控制器故障代码列表及原因分析)

The code is the LED flash count and the ErrorCode the programmer shows.

| Code | Chinese | CN ours | Shinegle English | Cause (CN ours) | Cause (Shinegle English) | Fix (CN ours) | Fix (Shinegle English) | Our note |
|---|---|---|---|---|---|---|---|---|
| 1 | 正常 | Normal | NO KNOWN FAULTS | 1. None | 1. Good | 1. None | 1. OK | The Mode B text says ErrorCode 0 = normal. This table starts at 1 = normal. |
| 2 | 电池电压低 | Battery voltage low | LOW BATTERY VOLTAGE | 1. Battery voltage below the controller's minimum working voltage<br>2. Battery terminal corrosion<br>3. Battery or controller terminal loose | 1. Battery Low Voltage<br>2. B+or B- terminal corrosion<br>3. Terminal of Battery or controller loosening. | 1. Bring the battery voltage above the controller's minimum working voltage | 1. Check battery voltage<br>2. Replace new terminal<br>3. Return to factory | The Chinese numbers 4 causes but prints 3. |
| 3 | U相电流传感器故障 | Phase U current sensor fault | PHASE U CURRENT SHUNT FAULT | 1. Wrong vehicle operation caused a high current spike<br>2. Current sensor out of range<br>3. Controller fault | 1. Current spike<br>2. Over range for current sensor<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller | 1. Reset the controller,<br>2. Return to factory |  |
| 4 | V相电流传感器故障 | Phase V current sensor fault | PHASE V CURRENT SHUNT FAULT | 1. Wrong vehicle operation caused a high current spike<br>2. Current sensor out of range<br>3. Controller fault | 1. Current spike<br>2. Over range for current sensor<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller | 1. Reset the controller<br>2. Reset the controller<br>3. Return to factory |  |
| 5 | 系统错误 | System error | System FAULT | 1. Heavy electrical noise<br>2. Overload | 1. Environmental noise<br>2. Overload | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller | 1. Reset the controller<br>2. Return to factory |  |
| 6 | U 相故障 | Phase U fault | PHASE U FAULT | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Environmental noise<br>2. Wrong dead time setup<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller | 1. Eliminate noise<br>2. Modify dead time<br>3. Return to factory |  |
| 7 | V 相故障 | Phase V fault | PHASE U FAULT | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Environmental noise<br>2. Wrong dead time setup<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller | 1. Eliminate noise<br>2. Modify dead time<br>3. Return to factory | English says PHASE U. The Chinese says phase V, which is right. |
| 8 | W 相故障 | Phase W fault | PHASE U FAULT | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Environmental noise<br>2. Wrong dead time setup<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller | 1. Eliminate noise<br>2. Modify dead time<br>3. Return to factory | English says PHASE U. The Chinese says phase W, which is right. |
| 9 | 电机温度传感器故障 | Motor temperature sensor fault | MOTOR SENSOR FAULT | 1. Motor temp sensor broken<br>2. Motor running too hot<br>3. Motor temp sensor wire loose | 1. Bad motor temperature sensor<br>2. Motor temperature too high<br>3. Sensor terminal loosening | 1. Replace the motor temp sensor<br>2. Let the motor cool back to normal<br>3. Reconnect the sensor wire | 1. Replace new sensor<br>2. Lower motor temperature<br>3. Tightening the terminal | The English just says "motor sensor". It is the motor temperature sensor, not the speed sensor (those are codes 20-23). |
| 10 | 预充电电压低 | Precharge voltage low | LOW PRECHARGE VOLTAG | 1. Precharge voltage below the set value<br>2. Precharge resistor fault | 1. Precharge voltage is low<br>2. Precharge circuit fault | 1. Bring the battery voltage back to normal<br>2. Replace the precharge resistor | 1. Recharge the battery<br>2. Return to factory | The Chinese says replace the precharge resistor. The English says return to factory. |
| 11 | 硬件安全故障 | Hardware safety fault | HW FAILSAFE | 1. Heavy electrical noise<br>2. Self-test or watchdog error<br>3. Controller fault | 1. Environmental noise<br>2. Self-test or watchdog fault<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller | 1. Lower environmental noise, return to factory if fault remains |  |
| 12 | 控制器温升故障 | Controller over-temperature | CONTROLLER HOT | 1. Temperature too high<br>2. Vehicle overloaded<br>3. Controller mounted wrong | 1. Controller temperature too high<br>2. Vehicle overload<br>3. inappropriate install | 1. Let the temperature come back to normal | 1. Lower temperature<br>2. Lower vehicle load<br>3. Proper installation |  |
| 13 | 主接触器或者制动器故障 | Main contactor or brake fault | CONTACTOR OR BRAKER FAULT | 1. Main contactor fault<br>2. Brake fault | 1. Main contactor fault<br>2. Breaker fault | 1. Replace the main contactor<br>2. Replace the brake | 1. Replace Main contactor<br>2. Replace breaker | 制动器 means brake (an electric brake device), not a circuit breaker. So the controller knows about some brake device. Which pin is not documented. See docs/brake-regen.md. |
| 14 | 电池电压过高 | Battery voltage too high | OVERVOLTAGE | 1. Battery voltage above the controller's top cut-off voltage<br>2. When the power comes from the grid (charger) or from generating (regen), braking… (cut off) | 1. Battery voltage too high<br>2. Breaking is too fast | 1. Bring the battery voltage below the controller's upper cut-off voltage | 1. Lower battery voltage<br>2. Lower break rate | Regen can push the pack over the limit, most likely when the pack is full. The English fix is to lower the brake rate (B_Rat). |
| 15 | 电池电压过低 | Battery voltage too low | TOO LOW BATTERY VOLTAGE | 1. Battery voltage too low<br>2. Power cut suddenly<br>3. Terminal loose | 1. Battery running voltage too low<br>2. Turn off suddenly<br>3. Connector terminal loosening | 1. Bring the battery voltage back to normal | 1. Return to normal value<br>2. No fault<br>3. Lightening terminal | "Lightening terminal" is a typo for tightening. |
| 16 | 预充电压2过低 | Precharge voltage 2 too low | PRECHARGE VOLTAGE TOO SLOW | 1. Precharge voltage too low<br>2. Charging (precharge) circuit fault | 1. Precharge voltage 2 too low<br>2. Precharge circuit fault | 1. Check the battery voltage<br>2. Replace the controller | 1. Return to normal value<br>2. Return to factory | English title says "too slow", the Chinese says too low. |
| 17 | 电路传感器故障1 | Current sensor 1 fault | CURRENT SENSOR 1 | 1. Current sensor 1 fault<br>2. Terminal loose | 1. Current sensor 1 fault<br>2. Phase terminal loosening | 1. Replace the current sensor<br>2. Tighten the terminal | 1. Replace current sensor<br>2. Lightening terminal | The Chinese title says 电路 (circuit), a typo for 电流 (current). |
| 18 | 电路传感器故障2 | Current sensor 2 fault | CURRENT SENSOR 1 | 1. Current sensor 1 fault (sic<br>2. should be 2)<br>3. Terminal loose | 1. Current sensor 2 fault<br>2. Phase terminal loosening | 1. Replace the current sensor<br>2. Tighten the terminal | 1. Replace current sensor<br>2. Lightening terminal | Each language has one slip. The English title says sensor 1, the Chinese cause says sensor 1. It is current sensor 2. |
| 19 | 电池电压高 | Battery voltage high | HIGH BATTERY VOLTAGE | 1. Battery voltage above the controller's set working voltage<br>2. Controller braking too fast | 1. Battery voltage 2 is too high<br>2. Breaking voltage is too high | 1. Bring the battery voltage below the controller's set working voltage<br>2. Lower the deceleration rate or make the deceleration time longer | 1. Return to normal value<br>2. Lower break rate | The Chinese fix points at the deceleration rate (DecRat), the English at the brake rate (B_Rat). Both are on page 4 and adjustable 3-36. |
| 20 | 速度编码器故障1 | Speed encoder fault 1 | ENCODER 1 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Speed sensor fault 1<br>2. Sensor interface loosening | 1. Replace the speed encoder<br>2. Replace the plug or the wiring | 1. Replace a new sensor<br>2. Replace a new connector |  |
| 21 | 速度编码器故障2 | Speed encoder fault 2 | ENCODER 2 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Speed sensor fault 2<br>2. Sensor interface loosening | 1. Replace the speed encoder<br>2. Replace the plug or the wiring | 1. Replace a new sensor<br>2. Replace a new connector |  |
| 22 | 速度编码器故障3 | Speed encoder fault 3 | ENCODER 3 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Speed sensor fault 3<br>2. Sensor interface loosening<br>3. No sensor | 1. Replace the speed encoder<br>2. Replace the plug or the wiring | 1. Replace a new sensor<br>2. Replace a new connector<br>3. Add a sensor | Only the English adds "no sensor / add a sensor". |
| 23 | 速度编码器故障4 | Speed encoder fault 4 | ENCODER 4 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Speed sensor fault 4<br>2. Interface loosening | 1. Replace the speed encoder<br>2. Replace the plug or the wiring | 1. Replace a new sensor<br>2. Replace a new connector |  |
| 24 | 系统负载故障1 | System load fault 1 | System Load Error 1 | 1. Motor missing a phase<br>2. Plug loose<br>3. Motor phases in the wrong order<br>4. Electrical noise | 1. Absence of Motor's Phase<br>2. Terminal of Battery or Controller Loosening<br>3. Wrong Phase Order of Motor<br>4. Environmental Noise | 1. Check motor phases U V W<br>2. Tighten the plug<br>3. Swap U and W<br>4. Remove the noise source | 1. Check Motor's Phase<br>2. Tight Terminal of Battery or Controller<br>3. Swap Phase U with W ot Motor<br>4. Lower Environmental Noise |  |
| 25 | 系统负载故障2 | System load fault 2 | System Load Error 2 | 1. Motor missing a phase<br>2. Plug loose<br>3. Motor phases in the wrong order<br>4. Electrical noise | 1. Absence of Motor's Phase<br>2. Terminal of Battery or Controller Loosening<br>3. Wrong Phase Order of Motor<br>4. Environmental Noise | 1. Check motor phases U V W<br>2. Tighten the plug<br>3. Swap U and W<br>4. Remove the noise source | 1. Check Motor's Phase<br>2. Tight Terminal of Battery or Controller<br>3. Swap Phase U with W ot Motor<br>4. Lower Environmental Noise |  |
| 26 | 电池电压低 | Battery voltage low (under load) | Low Running Battery Voltage | 1. Load too high<br>2. Battery charge low<br>3. Battery post or controller terminal loose | 1. Over Load<br>2. Low battery voltage<br>3. Terminal of Battery or Controller Loosening | 1. Reduce the load<br>2. Charge<br>3. Tighten the terminals | 1. Decrease Load<br>2. Charge Battery<br>3. Tight Terminal of Battery or Controller |  |
| 27-29 | 预留 | Reserved | Reserved |  |  |  |  |  |
| 30 | 参数Kf设置错误 | Parameter Kf set wrong | Parameter Kf Wrong Setting | 1. Parameter set wrong | 1. Wrong Setting | 1. Set the correct value | 1. Set Right Value |  |
| 31-37 | 系统错误2 | System error 2 | System Error 2 | 1. Electrical noise<br>2. Hardware error | 1. Environmental Noise<br>2. Hardware Fault | 1. Reduce the noise<br>2. Restart<br>3. If it still happens<br>4. send it back to the factory | 1. Lower Environmental Noise<br>2. Restart<br>3. Return to Factory |  |
| 38-42 | 预留 | Reserved | Reserved |  |  |  |  |  |
| 43-46 | 无刷直流控制器专用 | Only for brushless DC (BLDC) controllers | Just For BLDC Controller |  |  |  |  |  |

### Fault causes and fixes in the original Chinese

| Code | 编程器显示 | 故障原因 | 解决方法 |
|---|---|---|---|
| 1 | 正常 | 1. 无 | 1. 无 |
| 2 | 电池电压低 | 1. 电池电压小于控制器最低工作电压<br>2. 电池端子腐蚀<br>3. 电池或控制器接线端子松动 | 1. 使电池电压高于控制器最低工作电压 |
| 3 | U相电流传感器故障 | 1. 车辆操作错误导致高电流尖锋<br>2. 电流传感器超范围<br>3. 控制器故障 | 1. 重新开启钥匙开关，如问题继续存在，更换控制器 |
| 4 | V相电流传感器故障 | 1. 车辆操作错误导致高电流尖锋<br>2. 电流传感器超范围<br>3. 控制器故障 | 1. 重新开启钥匙开关，如问题继续存在，更换控制器 |
| 5 | 系统错误 | 1. 环境干扰大<br>2. 过载 | 1. 重新开启钥匙开关，如问题继续存在，更换控制器 |
| 6 | U 相故障 | 1. 环境干扰大<br>2. 死区时间设置不当<br>3. 控制器故障 | 1. 减少环境干扰<br>2. 调整死区时间<br>3. 如问题继续存在，更换控制器 |
| 7 | V 相故障 | 1. 环境干扰大<br>2. 死区时间设置不当<br>3. 控制器故障 | 1. 减少环境干扰<br>2. 调整死区时间<br>3. 如问题继续存在，更换控制器 |
| 8 | W 相故障 | 1. 环境干扰大<br>2. 死区时间设置不当<br>3. 控制器故障 | 1. 减少环境干扰<br>2. 调整死区时间<br>3. 如问题继续存在，更换控制器 |
| 9 | 电机温度传感器故障 | 1. 电机温度传感器坏<br>2. 电机温升过高<br>3. 电机温度传感器线松动 | 1. 更换电机温度传感器<br>2. 使电机温升恢复正常值<br>3. 接好传感器线 |
| 10 | 预充电电压低 | 1. 电池预充电电压小于设定值<br>2. 预充电电阻故障 | 1. 使电池电压恢复正常值<br>2. 更换预充电电阻 |
| 11 | 硬件安全故障 | 1. 环境干扰大<br>2. 自检或看门狗出错<br>3. 控制器故障 | 1. 重新开启钥匙开关，如问题继续存在，更换控制器 |
| 12 | 控制器温升故障 | 1. 温度过高<br>2. 车辆过载<br>3. 控制器安装错误 | 1. 使温度恢复至正常值 |
| 13 | 主接触器或者制动器故障 | 1. 主接触器故障<br>2. 制动器故障 | 1. 更换主接触<br>2. 更换制动器 |
| 14 | 电池电压过高 | 1. 电池电压高于控制器最高截止工作电压<br>2. 电源来自电网或者发电时，制… (cut off) | 1. 使电池电压低于控制器上限截止工作电压 |
| 15 | 电池电压过低 | 1. 电池电压过低<br>2. 突然断电<br>3. 接线端子松动 | 1. 使电池电压恢复至正常值 |
| 16 | 预充电压2过低 | 1. 预充电电压太低<br>2. 充电电路故障 | 1. 检查电池电压<br>2. 更换控制器 |
| 17 | 电路传感器故障1 | 1. 电流传感器1故障<br>2. 端子松动 | 1. 更换电流传感器<br>2. 拧紧端子 |
| 18 | 电路传感器故障2 | 1. 电流传感器1故障<br>2. 端子松动 | 1. 更换电流传感器<br>2. 拧紧端子 |
| 19 | 电池电压高 | 1. 电池电压高于控制器设定工作电压<br>2. 电压控制器制动过快 | 1. 使电池电压低于控制器设定工作电压<br>2. 减小减速速率或者延长减速时间 (bottom line partly cut off) |
| 20 | 速度编码器故障1 | 1. 速度编码器坏<br>2. 接口松动或断线 | 1. 更换速度编码器<br>2. 更换接插件或接线 |
| 21 | 速度编码器故障2 | 1. 速度编码器坏<br>2. 接口松动或断线 | 1. 更换速度编码器<br>2. 更换接插件或接线 |
| 22 | 速度编码器故障3 | 1. 速度编码器坏<br>2. 接口松动或断线 | 1. 更换速度编码器<br>2. 更换接插件或接线 |
| 23 | 速度编码器故障4 | 1. 速度编码器坏<br>2. 接口松动或断线 | 1. 更换速度编码器<br>2. 更换接插件或接线 |
| 24 | 系统负载故障1 | 1. 电机缺相<br>2. 接口松动<br>3. 电机相序接反<br>4. 环境干扰 | 1. 检查电机UVW相<br>2. 拧紧接口<br>3. 对调UW相<br>4. 消除干扰源 |
| 25 | 系统负载故障2 | 1. 电机缺相<br>2. 接口松动<br>3. 电机相序接反<br>4. 环境干扰 | 1. 检查电机UVW相<br>2. 拧紧接口<br>3. 对调UW相<br>4. 消除干扰源 |
| 26 | 电池电压低 | 1. 负载过大<br>2. 电池电量不足<br>3. 电池接线柱子或控制器接线端子松动 | 1. 减小负载<br>2. 充电<br>3. 拧紧接线端子 |
| 27-29 | 预留 |  |  |
| 30 | 参数Kf设置错误 | 1. 参数设置错误 | 1. 设置正确的参数 |
| 31-37 | 系统错误2 | 1. 环境干扰<br>2. 硬件错误 | 1. 减少干扰<br>2. 重启<br>3. 如错误仍然发生，返厂维修 |
| 38-42 | 预留 |  |  |
| 43-46 | 无刷直流控制器专用 |  |  |
