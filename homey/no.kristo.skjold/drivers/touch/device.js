'use strict';

const SkjoldDevice = require('../../lib/SkjoldDevice');

class TouchDevice extends SkjoldDevice {
  static get PRODUCT() { return 'touch'; }
}

module.exports = TouchDevice;
