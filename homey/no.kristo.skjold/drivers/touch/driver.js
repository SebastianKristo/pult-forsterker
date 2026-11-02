'use strict';

const SkjoldDriver = require('../../lib/SkjoldDriver');

class TouchDriver extends SkjoldDriver {
  static get PRODUCT() { return 'touch'; }
}

module.exports = TouchDriver;
