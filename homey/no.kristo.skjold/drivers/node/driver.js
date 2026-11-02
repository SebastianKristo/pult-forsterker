'use strict';

const SkjoldDriver = require('../../lib/SkjoldDriver');

class NodeDriver extends SkjoldDriver {
  static get PRODUCT() { return 'node'; }
}

module.exports = NodeDriver;
