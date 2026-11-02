'use strict';

const SkjoldDriver = require('../../lib/SkjoldDriver');

class CoreDriver extends SkjoldDriver {
  static get PRODUCT() { return 'core'; }
}

module.exports = CoreDriver;
