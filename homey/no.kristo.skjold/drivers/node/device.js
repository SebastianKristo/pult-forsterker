'use strict';

const SkjoldDevice = require('../../lib/SkjoldDevice');

class NodeDevice extends SkjoldDevice {
  static get PRODUCT() { return 'node'; }
}

module.exports = NodeDevice;
