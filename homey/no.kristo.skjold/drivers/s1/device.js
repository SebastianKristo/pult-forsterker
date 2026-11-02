'use strict';

const SkjoldDevice = require('../../lib/SkjoldDevice');

class S1Device extends SkjoldDevice {
  static get PRODUCT() { return 's1'; }
}

module.exports = S1Device;
