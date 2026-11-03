'use strict';

module.exports = {
  async getAll({ homey }) {
    const out = [];
    for (const d of homey.app.skjoldDevices()) {
      try { const s = await d.widgetState(); out.push({ id: d.getData().id, ...s, presets: undefined }); } catch (e) { /* hopp over */ }
    }
    return out;
  },
  async action({ homey, body }) {
    const d = homey.app.widgetDevice(body.device);
    await d.widgetAction(body);
    await new Promise((r) => setTimeout(r, 250));
    return { id: body.device, ...(await d.widgetState()), presets: undefined };
  },
};
