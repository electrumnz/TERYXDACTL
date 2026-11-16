// Only the browser (WebUSB) parts of node-carplay that the dash needs. No microphone yet.
import { Buffer } from "buffer";
globalThis.Buffer = globalThis.Buffer || Buffer;
export { default as CarplayWeb, findDevice, requestDevice, isCarplayDongle } from "node-carplay/dist/web/CarplayWeb.js";
export { DongleDriver, DEFAULT_CONFIG, HandDriveType } from "node-carplay/dist/modules/DongleDriver.js";
export { SendTouch, TouchAction, SendCommand } from "node-carplay/dist/modules/messages/sendable.js";
export { decodeTypeMap, AudioCommand, PhoneType } from "node-carplay/dist/modules/messages/readable.js";
