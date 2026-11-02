'use strict';

const SkjoldDevice = require('../../lib/SkjoldDevice');

class CoreDevice extends SkjoldDevice {
  static get PRODUCT() { return 'core'; }
}

module.exports = CoreDevice;
