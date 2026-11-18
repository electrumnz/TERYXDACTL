# Shinegle SG1810 handheld programmer: our copy of the manual

Source: "6_Programmer SG1810 Instruction English 20220415", a two-language
(Chinese and English) manual. Sam sent screenshots of it on 2026-11-18. This
is our own copy of all its text, with:

* the Chinese as printed,
* **CN ours**: our own translation of the Chinese, so we can check Shinegle's English,
* Shinegle's English as printed (typos kept),
* a list of where the two languages disagree.

The two big tables (parameters and fault codes) are machine readable:
[`config/shinegle-sg1810-params.yaml`](../config/shinegle-sg1810-params.yaml) and
[`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml), shown as tables in
[`shinegle-sg1810-tables.md`](shinegle-sg1810-tables.md).

Nothing here is guessed. Where text runs off a screenshot it says "cut off".
**Missing:** Fig. 4 (probably the keypad) wasn't in the screenshots.

## What matters for Teryx OS

* **Regen strength is `B_Cur`** (page 9, "Regenerative brake Coefficient",
  512-4096). Shinegle mark it "prohibited to change without authorized" and
  it is not green, so changing it needs Shinegle's OK.
* **`B_Rat` (brake rate) and `DecRat` (deceleration rate)** on page 4 are
  green, so Shinegle allow changing them: default 12, range 3-36. These are the
  safe knobs to try for stronger or softer engine braking. Faults 14 and 19
  say a rate set too high can over-volt the battery, most likely when it is
  full. See [`brake-regen.md`](brake-regen.md).
* **Fault 13 is "main contactor or brake fault".** The Chinese 制动器 means a
  brake device (the English says "breaker"). So the controller watches some
  kind of brake, but which pin is still unknown.
* **The programmer plugs into J3**, a 6-pin 5557-6P (Molex Mini-Fit style)
  socket, not J1. See [The programmer port](#the-programmer-port-j3).
* **Plugging something into J3 before key-on stops the controller driving.**
  It goes into parameter mode instead. Anything we leave on J3 must stay quiet
  at key-on. See [Leaving the Pi on J3](#leaving-the-pi-on-j3-instead-of-the-programmer).
* **Live data on J3 (Mode B):** error code, direction, throttle (0-1023),
  throttle switch, motor RPM, motor temp, battery volts, motor on/off. That's
  what the Pi could show on the dash.

## Intro

> 本编程器以非常简洁的界面实现参数的更改和运行参数的监控。控制器的参数绝大部分都是已经优化过的，不可更改，擅自更改参数有可能导致不可预知的错误产生甚至烧毁控制器，慎用！需要更改参数时，请提前详细阅读本指南！

CN ours: This programmer changes parameters and monitors running data through a
very simple screen. Nearly all the controller's parameters are already
optimised and must not be changed. Changing them without permission can cause
unexpected faults or even burn out the controller. Use with care! Read this
guide fully before changing anything.

> This Programmer can change parameters of controller and watch running status of controller by clean interface. Also most parameters of controller are optimized and no change, changing parameter without authorized may cause unexpected damage for controller, please read carefully this instruction before changing parameter.

## 1. Outline drawing (编程器产品外观图)

> 1、编程器产品外观图 (outline drawing of SG Programmer):
> 图 1 编程器外观图 (Fig.1 outline drawing of programmer)

The photo shows the handheld (screen; three LEDs; arrow keys round an Enter
key; − and +; PgUp, Mode, PgDn, Light) and its lead: a blue cable with a
**USB-A shaped plug** on one end and a **white 6-pin plug in red sleeving** on
the other, plus a black coiled cable. The USB-A shape is only the connector.
It is not USB (the controller's own manual puts +12 V on this lead).

## 2. Connecting to the controller (与控制器连接图)

> 2、与控制器连接图 (connect to controller):
> 图 2 控制器与编程器连接图 (Fig.2 connecting with controller)

The photo shows the red-sleeved 6-pin plug going into a small socket on the
top edge of an SG12xx "AC CONTROLLER", next to the larger signal plug.

## 3. How to use it (使用方法 / instruction)

> 本编程器为 SHINEGLE 控制器专用，严禁接到任何其他通讯设备或者其他公司的控制器上，否则引起的一切后果由其本人负责。

CN ours: This programmer is only for SHINEGLE controllers. Never connect it to
any other communication device or another company's controller. Any result of
doing so is your own responsibility.

> This hand-held programmer is just for "SHINEGLE" controller, connecting with any other communication devices or controller of other company is strictly prohibited! Otherwise, you will be held responsible for all the consequences arising therefrom.
>
> Programmer has two modes, mode A is for changing parameter, mode B is for status monitor, the following description will teach you how to enter different modes(Mode A and Mode B) of programmer.

(The second English paragraph has no Chinese version.)

### Mode A: parameter modification (进入参数修改模式)

> 首先把编程器的6pin插头（5557-6P）插入控制器的J3插座上，如图2所示，然后再打开钥匙给控制器上电，这样才能进入参数修改模式，所有参数见附表1，显示的参数如下图3所示：

CN ours: First plug the programmer's 6-pin plug (5557-6P) into the
controller's J3 socket, as in Fig. 2. Then turn the key on to power the
controller. Only this way does it enter parameter mode. All the parameters are
in attached list 1. The screen looks like Fig. 3:

> At first, plug 6-pin header(5557-6P) of hand-held programmer into J3 female connector of controller, as shown in fig.2, then turn off the key switch, turn on the key switch, in this order, the controller will be entered into mode of changing parameter. For details see attached table 1, the displayed parameter see the following picture 3:

> 图 3 参数显示界面 (Fig.3 parameter interface)
>
> Parameter 为参数名，Page 表示参数所在的页数，Value 表示参数的值。
> Parameter --parameter name, Page-parameters in page, Value-value of parameter

The Fig. 3 photo shows page 0: `F_Spd: 0 8300`, `F_Spd2: 5000`,
`R_Spd: 3500`, `Kf: 300`.

### Keys

> 符号▼和▲为参数选择键，符号◀和▶为备用键，符号"+"和"-"为参数修改键，符号"Enter"为参数确认键，PgUp 键为向上翻页，PgDn 键为向下翻页，Mode 为系统保留键，Light 为 LED 灯开关键。

CN ours: ▼ and ▲ pick the parameter. ◀ and ▶ are spare keys. + and − change
the value. Enter confirms. PgUp pages up, PgDn pages down. Mode is reserved by
the system. Light switches the LED (backlight) on and off.

> ▼and▲ -parameter selection, ◀ and ▶ --backup key, + and - parameter change "Enter" parameter validation

> "+"键将根据参数性质自动增加所选参数的值，长按"+"将快速增加参数的值，"-"键将根据参数性质自动减小所选参数的值，长按"-"将快速减小参数的值。

CN ours: + raises the selected value by a step that suits that parameter.
Hold + to raise it fast. − lowers it the same way. Hold − to lower it fast.

> "+"will increase value of selected value, press and hold "+" will increase value of parameter very fast, "-"will decrease value of parameter, press and hold "-" will decrease value of parameter very fast.

> PgUp 和 PgDn 键将实现参数的翻页功能。
> Pgup—page up PgDn—page down

> 当参数调整到合适值时，按 Enter 键将出现参数更新的确认画面，如果确认参数无误，再按一下 Enter 键,参数将修改成功，按其他键将放弃当前修改的参数。确认画面如图 5 所示。

CN ours: When the value is right, press Enter and a confirm screen comes up.
If it's correct, press Enter again and the change is saved. Any other key
throws the change away. The confirm screen is Fig. 5.

> When the selected parameter is set to the suitable value, press "Enter" key, then "Updated Really" screen will display, you can press "Enter" key again to confirm change if you think the parameter is ok, press other key to exit parameter change if you think the changed parameter is wrong and the value will not be updated.

> 图 5 参数更新确认界面 (Fig.5 confirm screen for parameter update)

The Fig. 5 screen reads: `Update Really?` / `Enter Key to Confirm` /
`Other Key to Exit`.

### Mode B: status monitor (进入控制器运行模式)

> 如果想查看控制器的运行状态，必须先断开编程器和控制器的连接，重新给控制器上电（未通电前，编程器和控制器处于连接状态是无法让控制器工作的），这样控制器才能进入正常工作状态，待控制器正常工作后，连接上编程器，这时编程器可以监控控制器的运行状态，控制器提供给编程器的运行参数如图 6 和图 7 所示。

CN ours: To watch the controller running, first unplug the programmer, then
power the controller up again. (If the programmer is plugged in before power
is on, the controller can't work.) Only then does the controller start
normally. Once it's running, plug the programmer in and it shows the running
status. The data the controller sends to the programmer is in Fig. 6 and 7.

> If you want to watch the running status of controller, please do it in the following order:
> 1. disconnect programmer with controller
> 2. turn on the key switch of controller
> 3. wait for about 5 seconds
> 4. plug 6-pin connector(5557-6P) of programmer intor female connector(6 PIN) of controller
> 5. after about 5 seconds, running status of controller is displayed
>
> The controller running parameters are shown as Fig.6 and Fig.7.

#### Status page 1 (图 6 页面 1 运行参数 / Fig.6 running parameters in page 1)

The Fig. 6 screen reads: `ErrorCode: 9`, `DIR: R/Rev`, `Pedal: 636`, `PedalSW: ON`.

| Item | Chinese | CN ours | Shinegle English |
|---|---|---|---|
| ErrorCode | 故障信号，0--控制器正常工作，大于 0—故障，故障代码见附表 2。 | Fault signal. 0 = controller working normally, above 0 = fault, codes in attached list 2. | Error code, 0—normal, >0:error code, see attached list 2 |
| Dir | 方向信号，NULL--空档，Fwd/D—前进档，Rev/R—后退档。 | Direction. NULL = neutral, Fwd/D = forward, Rev/R = reverse. | Dir: direction, NULL--no direction,Fwd/D--forward,Rev/R--Reverse |
| Pedal | 油门值（0～1023） | Throttle value (0-1023) | Pedal:pedal value, range: 0-1023 |
| Pedal SW | 油门踏板的微动信号，OFF—微动信号关，ON—微动信号开。 | Throttle pedal micro switch. OFF = off, ON = on. | Pedal SW: Pedal micro switch status, OFF-Off status, ON-ON status |

#### Status page 2 (图 7 页面 2 运行参数 / Fig.7 running parameters in page 2)

The Fig. 7 screen reads: `Spd(RPM): 0`, `MotorTemp: NULL`, `VOLT(V): 28`, `Motor: OFF`.

| Item | Chinese | CN ours | Shinegle English |
|---|---|---|---|
| Spd(RPM) | 电机实际转速，单位 RPM。 | Actual motor speed, in RPM. | Spd (RPM) :motor speed, unit--RPM |
| MotorTemp | 电机温度，NULL 表示未接电机温度传感器。 | Motor temperature. NULL means no motor temp sensor is connected. | MotorTemp: motor temperature, unit—degree centigrade |
| VOLT(V) | 电池电压。 | Battery voltage. | VOLT(V): battery voltage, unit--V |
| Motor | 电机运行状态，ON—电机运行，OFF—电机停止。 | Motor state. ON = running, OFF = stopped. | Motor: motor status, ON-Running, OFF-stop |

## Attached list 1 and 2

Both tables, in full and in both languages, are in
[`shinegle-sg1810-tables.md`](shinegle-sg1810-tables.md) (made from the YAML files).

## Where the Chinese and English disagree

Text and modes:

1. **Mode A key sequence.** Chinese: plug in, *then* turn the key on. English:
   plug in, then key off, then key on. Same idea (the programmer must be
   connected at power-up), but the English adds a key-off step.
2. **Mode B warning.** Only the Chinese says that if the programmer is
   connected before power-up the controller can't work. The English just gives
   the steps. This matters for leaving a Pi on J3 (see below).
3. **Mode key and Light key.** Only the Chinese says Mode is reserved by the
   system and Light switches the LED. The English calls ◀ ▶ "backup" keys
   (Chinese: spare keys).
4. **MotorTemp NULL.** Only the Chinese says NULL means no sensor fitted. The
   English adds the unit (°C) instead.
5. **ErrorCode 0 vs 1.** The status page says 0 = normal. The fault table
   says code 1 = no fault. Both languages agree with each other on this; the
   manual just isn't consistent.
6. **Final note on the parameter table.** The English adds "with our
   permission" and "different controller has different default value". The
   Chinese only says the green ones on pages 0 and 4 can be tuned to the
   vehicle's load.

Parameter table (details in the YAML `note` fields):

7. **B_Trat:** Chinese "braking current response"; English adds "2".
8. **B_Trat3:** named B_ (brake) but both languages describe *reverse* current 3.
9. **DecRat2:** English adds "for backward"; the Chinese is just deceleration rate 2.
10. **F_Rat2** appears twice (page 3 value 10, page 5 value 18). Page 5's
    Chinese says "acceleration rate 2", the English "forward speed 3".
11. **F_Spd:** value 8000-13800 but the remark range is 8000-16000. Green, yet
    the remark says no need to adjust.
12. **R_Spd:** only the Chinese says it can be adjusted. Fig. 3 shows 3500,
    below the table's 6000 minimum.
13. **Slope:** English adds "Stop Voltage Coefficient", the Chinese says only reserved.
14. **B_Cur:** only the English remark says "Regenerative brake Coefficient".
    The Chinese is 刹车系数 (brake coefficient) with no remark.
15. **Ra_X10:** Chinese 差速器 (differential, here the final drive), English
    "Reduction Ratio". Same thing in practice.

Fault table:

16. **6, 7, 8:** English calls all three PHASE U FAULT. The Chinese has U, V and W.
17. **13:** English "breaker", Chinese 制动器 = brake.
18. **18:** English title says CURRENT SENSOR 1; the Chinese cause says sensor 1.
    It's current sensor 2.
19. **9:** English "MOTOR SENSOR"; the Chinese says motor *temperature* sensor.
20. **10:** Chinese fix is replace the precharge resistor; English says return to factory.
21. **14 and 19:** the Chinese links over-voltage to braking/generating; the
    Chinese fix for 19 is lower the deceleration rate, the English fix is lower
    the brake rate.
22. **16:** English "too slow", Chinese "too low".
23. **22:** only the English adds "no sensor / add a sensor".
24. **2:** the Chinese numbers four causes but lists three.

## The programmer port (J3)

This manual says the programmer's **6-pin 5557-6P plug goes into J3**. The
controller manual (SG12X2) draws the programmer on four **J1** pins instead
(+12 V J1-25, Tx J1-28, Rx J1-29, GND J1-7), and Sam described a 4-pin plug.
Most likely J3 is a separate 6-pin socket that carries the same four signals
(with two spare), but that's **TBC**. To check on Sam's controller:

* Is there a 6-pin socket marked J3 on the case or the harness? Photo it.
* Which of its pins have wires? Meter each to J1-25, J1-28, J1-29 and J1-7
  (power off, continuity mode).
* Key on, programmer unplugged: measure each J3 pin to ground. One should be
  about +12 V. The Tx line resting voltage tells us the logic level.

The pinout file [`config/shinegle-sg1202.yaml`](../config/shinegle-sg1202.yaml)
lists J3 with this marked TBC.

## Leaving the Pi on J3 instead of the programmer

Sam's idea (2026-11-18): drop the handheld and leave the Pi 5 (or the Pico)
plugged into J3 all the time, reading the Mode B data live for the dash.

That's a good fit: Mode B already gives error code, direction, throttle,
throttle switch, motor RPM, motor temp, battery volts and motor on/off. The
dash could show the fault by name (from
[`config/shinegle-faults.yaml`](../config/shinegle-faults.yaml), via
`teryx.shinegle_manual.fault(code)`), plus speed from RPM and the controller's
own voltage reading.

The catch: the manual says that if the programmer is connected at power-up,
the controller won't drive (it goes into parameter mode). We don't yet know
*how* it detects the programmer (a pin pulled to ground, or bytes on the
serial line). So the plan, in order:

1. **Listen-only sniff.** Tap the Tx and Rx lines between the handheld and J3
   (a Y lead, nothing replaced) with a cheap logic analyser or a USB serial
   adapter on its Rx pin only, through a resistor divider if it's 12 V logic.
   Record: key-on with the programmer plugged in (Mode A), and the Mode B
   sequence (key on, wait 5 s, plug in). Write down which pins the handheld
   pulls high or low when it's plugged in. Goal: baud rate, framing, the
   request the handheld sends, and the reply layout for each status field.
   Map them by moving one thing at a time (throttle, F/N/R, wheels turning).
2. **Read-only reader on the bench.** A small board that plays the handheld's
   Mode B role only: it sends the exact status request we recorded and
   decodes the reply. It never sends anything we didn't see the handheld send
   in Mode B. Test it with the motor off the ground first.
3. **Stay quiet at key-on.** The reader keeps its lines disconnected (or in
   whatever idle state the sniff shows is "no programmer") until about 5 s
   after the controller has started, then connects, just like the manual's
   Mode B steps. If the controller ever comes up in parameter mode with the
   reader fitted, that's a fail: unplug it and go back to step 1.
4. **Isolate the 12 V.** The J3/J1 port carries +12 V from the controller.
   Don't use it to power the Pi or the Pico, and don't join the controller's
   ground to the Pi's ground directly. Use a digital isolator or optocouplers
   on Tx and Rx, powered from our side, so a fault in the traction system
   can't reach the Pi. Which side of the isolator talks to the Pi or Pico is a
   later choice; the Pico control box is the safer home since it already owns
   the controller side.
5. **No writing parameters.** Mode A (changing settings) stays off the table
   until we fully understand the protocol, and even then only for the green
   parameters. The handheld stays in the glovebox for changes.

Until step 1 is done, nothing gets left plugged into J3.
