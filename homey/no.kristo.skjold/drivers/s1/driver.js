'use strict';

const SkjoldDriver = require('../../lib/SkjoldDriver');

class S1Driver extends SkjoldDriver {
  static get PRODUCT() { return 's1'; }
}

module.exports = S1Driver;
