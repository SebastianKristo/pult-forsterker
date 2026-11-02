'use strict';

module.exports = {
  async getState({ homey, query }) {
    return homey.app.widgetDevice(query.device).widgetState();
  },
  async action({ homey, body }) {
    const d = homey.app.widgetDevice(body.device);
    await d.widgetAction(body);
    await new Promise((r) => setTimeout(r, 250));
    return d.widgetState();
  },
};
