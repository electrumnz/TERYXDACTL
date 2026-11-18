# SG1810 programmer: parameter and fault tables

Made by `python -m teryx shinegle-manual` from
[`config/shinegle-sg1810-params.yaml`](../config/shinegle-sg1810-params.yaml) and
[`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml). Edit those, not this file.
The rest of the manual is in [`shinegle-sg1810-programmer.md`](shinegle-sg1810-programmer.md).

The Chinese is from the manual. The English is our own translation of it.
Values are "for reference only" (the manual's words) and won't match every controller.

## Parameters (附表1 编程器参数)

**Green** = green in the manual, the only ones Shinegle allow changing (to suit the vehicle's load).

| Page | Name | Value | 说明 | Description | 备注 | Remark | Note |
|---|---|---|---|---|---|---|---|
| 0 | **F_Spd** (green) | 8000-13800 | 最大前进速度系数 | Max forward speed coefficient | 已最优，无需调整，乘 0.5 为设定的最大速度 F_Spd :8000~16000 | Already optimal, no need to adjust. Top speed = 0.5 x F_Spd. Range 8000-16000. | The value column says 8000-13800. Green in the manual even though it says no need to adjust. |
| 0 | F_Spd2 | 5000 | 最大前进速度 2 系数 | Max forward speed 2 coefficient | 特殊车辆用，乘 0.5 为设定速度 | For special vehicles. Speed = 0.5 x F_Spd2. |  |
| 0 | **R_Spd** (green) | 6144 | 最大后退速度系数 | Max reverse speed coefficient | 可适当调整，乘 0.5 为设定的最大速度 R_Spd: 6000~10000 | Can be adjusted to suit. Top reverse speed = 0.5 x R_Spd. Range 6000-10000. | The manual photo of page 0 shows F_Spd 8300, R_Spd 3500 and Kf 300, so real controllers differ from this table. |
| 0 | Kf |  | 系统参数 | System parameter | 内部数据，禁止修改 | Internal data, do not change. |  |
| 1 | R_Trat2 | 24 | 后退电流 2 响应系数 | Reverse current 2 response coefficient | 特殊车辆用 | For special vehicles. |  |
| 1 | B_Trat2 | 24 | 制动电流 2 响应系数 | Braking current 2 response coefficient | 特殊车辆用 | For special vehicles. |  |
| 1 | F_Trat | 64 | 前进电流响应系数 | Forward current response coefficient | 已优化 , F_Trat: 24~72 | Already optimised. F_Trat: 24-72. |  |
| 1 | R_Trat | 24 | 后退电流响应系数 | Reverse current response coefficient | 已优化 R_Trat: 24~64 | Already optimised. R_Trat: 24-64. |  |
| 2 | B_Trat | 32 | 制动电流响应系数 | Braking current response coefficient | 已优化 B_Trat: 24~64 | Already optimised. B_Trat: 24-64. |  |
| 2 | F_Trat3 | 32 | 前进电流 3 响应系数 | Forward current 3 response coefficient | 特殊车辆用 | For special vehicles. |  |
| 2 | Neut_K | 32 | 预留 | Reserved | 预留 | Reserved. |  |
| 2 | B_Trat3 | 24 | 后退电流 3 响应系数 | Reverse current 3 response coefficient | 特殊车辆用 | For special vehicles. | Named B_ (brake) but described as reverse current 3. |
| 3 | F_Rat2 | 10 | 前进加速率 2 | Forward acceleration rate 2 | 特殊车辆用 | For special vehicles. |  |
| 3 | R_Rat2 | 18 | 后退加速率 2 | Reverse acceleration rate 2 | 特殊车辆用 | For special vehicles. |  |
| 3 | DecRat2 | 10 | 减速率 2 | Deceleration rate 2 | 特殊车辆用 | For special vehicles. |  |
| 3 | BrkRat2 | 24 | 制动速率 2 | Braking rate 2 | 特殊车辆用 | For special vehicles. |  |
| 4 | **F_Rat** (green) | 18 | 前进加速率 | Forward acceleration rate | 可修改，F_Rat: 3~36 | Can be changed. F_Rat: 3-36. |  |
| 4 | **R_Rat** (green) | 12 | 后退加速率 | Reverse acceleration rate | 可修改，R_Rat: 3~36 | Can be changed. R_Rat: 3-36. |  |
| 4 | **DecRat** (green) | 12 | 减速率 | Deceleration rate | 可修改，DecRat: 3~36 | Can be changed. DecRat: 3-36. |  |
| 4 | **B_Rat** (green) | 12 | 制动速率 | Braking rate | 可修改，B_Rat: 3~36 | Can be changed. B_Rat: 3-36. |  |
| 5 | EmrgK | 24 | 预留 | Reserved | 预留 | Reserved. |  |
| 5 | IncRat3 | 18 | 加速率 3 | Acceleration rate 3 | 特殊车辆用 | For special vehicles. |  |
| 5 | F_Rat2 | 18 | 加速率 2 | Acceleration rate 2 | 特殊车辆用 | For special vehicles. | The manual lists F_Rat2 twice (page 3 value 10, page 5 value 18). Check on the handheld. |
| 5 | Pls_Mt | 32/48/64 | 电机脉冲 | Motor pulses | 严禁修改 | Do not change. |  |
| 6 | Func | 224 | 系统特殊功能 | System special function | 系统参数 | System parameter. Do not change without permission. |  |
| 6 | ConstT | 200 | 预留 | Reserved |  | Reserved. Range 20-1500. |  |
| 6 | TorqM |  | 预留 | Reserved |  | Do not change. |  |
| 6 | Bvolt | 24~144 | 电池电压 | Battery voltage | 预设好 | Preset. Do not change without permission. |  |
| 7 | Func2 | 0/2 | 系统特殊功能 2 | System special function 2 | 系统参数 | System parameter. Do not change. |  |
| 7 | NC | 0/2 | 预留 | Reserved | 系统参数 | System parameter. |  |
| 7 | K1 | 6144 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 7 | K2 | 480 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 8 | K3 | 590 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 8 | K4 | 4096 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 8 | K5 | 480 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 8 | K6 | 650 | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| 9 | B_Cur | 512-4096 | 刹车系数 | Brake (regen) coefficient |  | Regenerative braking coefficient. Do not change without permission. |  |
| 9 | Slope |  | 预留 | Reserved | 预留 | Reserved. Do not change without permission. |  |
| 9 | EmgSpd | 378 | 预留 | Reserved | 预留 | Reserved. |  |
| 9 | EmgTm | 141 | 预留 | Reserved | 预留 | Reserved. |  |
| a | KF0 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| a | KF1 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| a | KF2 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| a | KF3 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| b | KD5 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| b | KD4 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| b | KD3 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| b | KD2 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| c | KD1 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| c | KD0 |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| c | BrkTm | 20000 | 预留 | Switch-off delay (reserved; meaning differs by controller type) | 关断延时，已优化 | Switch-off delay in ms, already optimised. Range 5000-20000. |  |
| c | OffTm | 0 | 预留 | Reserved | 预留 | Reserved. |  |
| d | PedSet | 50 | 油门初始值 | Throttle starting value (offset) | 严禁擅自修改 | Do not change without permission. |  |
| d | CDMax |  | 预留 | Reserved | 严禁擅自修改 | Do not change without permission. |  |
| d | F_Trat2 | 24 | 前进电流 2 响应系数 | Forward current 2 response coefficient | 特殊车辆用 | For special vehicles. |  |
| d | TypDia | 52 | 轮胎参数，预留 | Tyre parameter, reserved | 系统参数 | System parameter. |  |
| e | Ra_X10 | 100 | 差速器参数，预留 | Differential (final drive) parameter, reserved | 系统参数 | System parameter. | Probably the ratio x 10, so 100 = 10:1. Not stated in the manual. |
| e | V3Set | 10240 | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |
| e | T3Set | 5120 | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |
| e | V1Set | 8192 | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |
| f | T1Set | 5120 | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |
| f | Soff3 |  | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |
| f | Soff1 |  | 系统预留 | System reserved | 严禁擅自修改 | Do not change without permission. |  |

备注：正常情况下，出厂的控制器均经过优化，性能达到最佳，第 0 页和 4 页的绿色标注的参数可以根据车辆的载重量进行适当修改，以获得最佳的客户体验和舒适度。

Footnote: Normally every controller is optimised at the factory for best performance. The green parameters on pages 0 and 4 can be adjusted to suit the vehicle's load, for the best experience and comfort. Default values differ between controllers.

## Fault codes (附表2 SHINEGLE 控制器故障代码列表及原因分析)

The code is the LED flash count and the ErrorCode the programmer shows.

| Code | Fault | Causes | Fixes | Note |
|---|---|---|---|---|
| 1 | Normal | 1. None | 1. None | The status screen shows ErrorCode 0 when there is no fault. |
| 2 | Battery voltage low | 1. Battery voltage below the controller's minimum working voltage<br>2. Battery terminal corrosion<br>3. Battery or controller terminal loose | 1. Bring the battery voltage above the controller's minimum working voltage |  |
| 3 | Phase U current sensor fault | 1. Wrong vehicle operation caused a high current spike<br>2. Current sensor out of range<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller |  |
| 4 | Phase V current sensor fault | 1. Wrong vehicle operation caused a high current spike<br>2. Current sensor out of range<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller |  |
| 5 | System error | 1. Heavy electrical noise<br>2. Overload | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller |  |
| 6 | Phase U fault | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller |  |
| 7 | Phase V fault | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller |  |
| 8 | Phase W fault | 1. Heavy electrical noise<br>2. Dead time set wrong<br>3. Controller fault | 1. Reduce the noise<br>2. Adjust the dead time<br>3. If it keeps happening<br>4. replace the controller |  |
| 9 | Motor temperature sensor fault | 1. Motor temp sensor broken<br>2. Motor running too hot<br>3. Motor temp sensor wire loose | 1. Replace the motor temp sensor<br>2. Let the motor cool back to normal<br>3. Reconnect the sensor wire |  |
| 10 | Precharge voltage low | 1. Precharge voltage below the set value<br>2. Precharge resistor fault | 1. Bring the battery voltage back to normal<br>2. Replace the precharge resistor |  |
| 11 | Hardware safety fault | 1. Heavy electrical noise<br>2. Self-test or watchdog error<br>3. Controller fault | 1. Cycle the key switch. If it keeps happening<br>2. replace the controller |  |
| 12 | Controller over-temperature | 1. Temperature too high<br>2. Vehicle overloaded<br>3. Controller mounted wrong | 1. Let the temperature come back to normal |  |
| 13 | Main contactor or brake fault | 1. Main contactor fault<br>2. Brake fault | 1. Replace the main contactor<br>2. Replace the brake | 制动器 is a brake device, so the controller watches some kind of brake. Which pin is not documented. See docs/brake-regen.md. |
| 14 | Battery voltage too high | 1. Battery voltage above the controller's top cut-off voltage<br>2. Braking too hard while power is coming back (charging or regen) | 1. Bring the battery voltage below the controller's upper cut-off voltage | Regen can push a full pack over the limit. Fix by lowering the brake rate (B_Rat) or decel rate (DecRat). |
| 15 | Battery voltage too low | 1. Battery voltage too low<br>2. Power cut suddenly<br>3. Terminal loose | 1. Bring the battery voltage back to normal |  |
| 16 | Precharge voltage 2 too low | 1. Precharge voltage too low<br>2. Charging (precharge) circuit fault | 1. Check the battery voltage<br>2. Replace the controller |  |
| 17 | Current sensor 1 fault | 1. Current sensor 1 fault<br>2. Terminal loose | 1. Replace the current sensor<br>2. Tighten the terminal |  |
| 18 | Current sensor 2 fault | 1. Current sensor 2 fault<br>2. Terminal loose | 1. Replace the current sensor<br>2. Tighten the terminal |  |
| 19 | Battery voltage high | 1. Battery voltage above the controller's set working voltage<br>2. Controller braking too fast | 1. Bring the battery voltage below the controller's set working voltage<br>2. Lower the deceleration rate or make the deceleration time longer | Lower DecRat (page 4, adjustable 3-36). |
| 20 | Speed encoder fault 1 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Replace the speed encoder<br>2. Replace the plug or the wiring |  |
| 21 | Speed encoder fault 2 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Replace the speed encoder<br>2. Replace the plug or the wiring |  |
| 22 | Speed encoder fault 3 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Replace the speed encoder<br>2. Replace the plug or the wiring |  |
| 23 | Speed encoder fault 4 | 1. Speed encoder broken<br>2. Plug loose or wire broken | 1. Replace the speed encoder<br>2. Replace the plug or the wiring |  |
| 24 | System load fault 1 | 1. Motor missing a phase<br>2. Plug loose<br>3. Motor phases in the wrong order<br>4. Electrical noise | 1. Check motor phases U V W<br>2. Tighten the plug<br>3. Swap U and W<br>4. Remove the noise source |  |
| 25 | System load fault 2 | 1. Motor missing a phase<br>2. Plug loose<br>3. Motor phases in the wrong order<br>4. Electrical noise | 1. Check motor phases U V W<br>2. Tighten the plug<br>3. Swap U and W<br>4. Remove the noise source |  |
| 26 | Battery voltage low (under load) | 1. Load too high<br>2. Battery charge low<br>3. Battery post or controller terminal loose | 1. Reduce the load<br>2. Charge<br>3. Tighten the terminals |  |
| 27-29 | Reserved |  |  |  |
| 30 | Parameter Kf set wrong | 1. Parameter set wrong | 1. Set the correct value |  |
| 31-37 | System error 2 | 1. Electrical noise<br>2. Hardware error | 1. Reduce the noise<br>2. Restart<br>3. If it still happens<br>4. send it back to the factory |  |
| 38-42 | Reserved |  |  |  |
| 43-46 | Only for brushless DC (BLDC) controllers |  |  |  |

### 中文原文 (the Chinese)

| 代码 | 编程器显示 | 故障原因 | 解决方法 |
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
| 13 | 主接触器或者制动器故障 | 1. 主接触器故障<br>2. 制动器故障 | 1. 更换主接触器<br>2. 更换制动器 |
| 14 | 电池电压过高 | 1. 电池电压高于控制器最高截止工作电压<br>2. 电源来自电网或者发电时，制… | 1. 使电池电压低于控制器上限截止工作电压 |
| 15 | 电池电压过低 | 1. 电池电压过低<br>2. 突然断电<br>3. 接线端子松动 | 1. 使电池电压恢复至正常值 |
| 16 | 预充电压2过低 | 1. 预充电电压太低<br>2. 充电电路故障 | 1. 检查电池电压<br>2. 更换控制器 |
| 17 | 电流传感器故障1 | 1. 电流传感器1故障<br>2. 端子松动 | 1. 更换电流传感器<br>2. 拧紧端子 |
| 18 | 电流传感器故障2 | 1. 电流传感器2故障<br>2. 端子松动 | 1. 更换电流传感器<br>2. 拧紧端子 |
| 19 | 电池电压高 | 1. 电池电压高于控制器设定工作电压<br>2. 电压控制器制动过快 | 1. 使电池电压低于控制器设定工作电压<br>2. 减小减速速率或者延长减速时间 |
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
