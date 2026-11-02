'use strict';

const SkjoldDriver = require('../../lib/SkjoldDriver');

/** Gammel driver (før 2.14, «Pultforsterker»): skjult ved ny paring (deprecated), men parede enheter virker videre. */
class PultforsterkerDriver extends SkjoldDriver {}

module.exports = PultforsterkerDriver;
