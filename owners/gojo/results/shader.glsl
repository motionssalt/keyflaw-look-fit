#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform sampler2D uTexture;
varying vec2 vTex;
uniform vec2 uTexelSize;
uniform float uColourCorrection;
uniform float uQuality;

// --- Plugin: colour (GLSL ES 1.00, 0 texture taps) ---
float msCurveR(float x) {
    float s = clamp(x, 0.0, 1.0) * 32.0;
    if (s < 16.0) {
        if (s < 8.0) {
            if (s < 4.0) {
                if (s < 2.0) {
                    if (s < 1.0) {
                        return mix(0.000000, 0.014656, s - 0.0);
                    } else {
                        return mix(0.014656, 0.016159, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.016159, 0.046240, s - 2.0);
                    } else {
                        return mix(0.046240, 0.014639, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.014639, 0.064317, s - 4.0);
                    } else {
                        return mix(0.064317, 0.098044, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.098044, 0.171928, s - 6.0);
                    } else {
                        return mix(0.171928, 0.263959, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.263959, 0.311586, s - 8.0);
                    } else {
                        return mix(0.311586, 0.459667, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.459667, 0.382940, s - 10.0);
                    } else {
                        return mix(0.382940, 0.277210, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.277210, 0.165178, s - 12.0);
                    } else {
                        return mix(0.165178, 0.127565, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.127565, 0.181570, s - 14.0);
                    } else {
                        return mix(0.181570, 0.183563, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.183563, 0.260216, s - 16.0);
                    } else {
                        return mix(0.260216, 0.326407, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.326407, 0.473657, s - 18.0);
                    } else {
                        return mix(0.473657, 0.602355, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.602355, 0.687416, s - 20.0);
                    } else {
                        return mix(0.687416, 0.718673, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.718673, 0.703820, s - 22.0);
                    } else {
                        return mix(0.703820, 0.554592, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.554592, 0.669826, s - 24.0);
                    } else {
                        return mix(0.669826, 0.742924, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.742924, 0.786208, s - 26.0);
                    } else {
                        return mix(0.786208, 0.730261, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.730261, 0.805599, s - 28.0);
                    } else {
                        return mix(0.805599, 0.873943, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.873943, 0.935563, s - 30.0);
                    } else {
                        return mix(0.935563, 0.997349, s - 31.0);
                    }
                }
            }
        }
    }
}

float msCurveG(float x) {
    float s = clamp(x, 0.0, 1.0) * 32.0;
    if (s < 16.0) {
        if (s < 8.0) {
            if (s < 4.0) {
                if (s < 2.0) {
                    if (s < 1.0) {
                        return mix(0.000000, 0.010928, s - 0.0);
                    } else {
                        return mix(0.010928, 0.017868, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.017868, 0.038356, s - 2.0);
                    } else {
                        return mix(0.038356, 0.036981, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.036981, 0.075871, s - 4.0);
                    } else {
                        return mix(0.075871, 0.099614, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.099614, 0.182901, s - 6.0);
                    } else {
                        return mix(0.182901, 0.257548, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.257548, 0.286960, s - 8.0);
                    } else {
                        return mix(0.286960, 0.337730, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.337730, 0.305226, s - 10.0);
                    } else {
                        return mix(0.305226, 0.230284, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.230284, 0.195499, s - 12.0);
                    } else {
                        return mix(0.195499, 0.185345, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.185345, 0.271291, s - 14.0);
                    } else {
                        return mix(0.271291, 0.298178, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.298178, 0.372489, s - 16.0);
                    } else {
                        return mix(0.372489, 0.440956, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.440956, 0.534802, s - 18.0);
                    } else {
                        return mix(0.534802, 0.598776, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.598776, 0.650615, s - 20.0);
                    } else {
                        return mix(0.650615, 0.675255, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.675255, 0.686279, s - 22.0);
                    } else {
                        return mix(0.686279, 0.599047, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.599047, 0.712831, s - 24.0);
                    } else {
                        return mix(0.712831, 0.816496, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.816496, 0.877781, s - 26.0);
                    } else {
                        return mix(0.877781, 0.879948, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.879948, 0.927654, s - 28.0);
                    } else {
                        return mix(0.927654, 0.957071, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.957071, 0.975124, s - 30.0);
                    } else {
                        return mix(0.975124, 0.995075, s - 31.0);
                    }
                }
            }
        }
    }
}

float msCurveB(float x) {
    float s = clamp(x, 0.0, 1.0) * 32.0;
    if (s < 16.0) {
        if (s < 8.0) {
            if (s < 4.0) {
                if (s < 2.0) {
                    if (s < 1.0) {
                        return mix(0.008766, 0.009024, s - 0.0);
                    } else {
                        return mix(0.009024, 0.014344, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.014344, 0.023300, s - 2.0);
                    } else {
                        return mix(0.023300, 0.043141, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.043141, 0.065693, s - 4.0);
                    } else {
                        return mix(0.065693, 0.090375, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.090375, 0.163441, s - 6.0);
                    } else {
                        return mix(0.163441, 0.218349, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.218349, 0.230673, s - 8.0);
                    } else {
                        return mix(0.230673, 0.236143, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.236143, 0.231140, s - 10.0);
                    } else {
                        return mix(0.231140, 0.191382, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.191382, 0.202742, s - 12.0);
                    } else {
                        return mix(0.202742, 0.206036, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.206036, 0.296012, s - 14.0);
                    } else {
                        return mix(0.296012, 0.327326, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.327326, 0.389823, s - 16.0);
                    } else {
                        return mix(0.389823, 0.458353, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.458353, 0.548921, s - 18.0);
                    } else {
                        return mix(0.548921, 0.610834, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.610834, 0.653923, s - 20.0);
                    } else {
                        return mix(0.653923, 0.676500, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.676500, 0.688453, s - 22.0);
                    } else {
                        return mix(0.688453, 0.617027, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.617027, 0.727266, s - 24.0);
                    } else {
                        return mix(0.727266, 0.846178, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.846178, 0.906381, s - 26.0);
                    } else {
                        return mix(0.906381, 0.933558, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.933558, 0.962623, s - 28.0);
                    } else {
                        return mix(0.962623, 0.985140, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.985140, 0.993785, s - 30.0);
                    } else {
                        return mix(0.993785, 1.000000, s - 31.0);
                    }
                }
            }
        }
    }
}

vec3 msLut9Node(int ir, int ig, int ib) {
    if (ir <= 4) {
      if (ir <= 2) {
        if (ir <= 1) {
          if (ir <= 0) {
            if (ig <= 4) {
              if (ig <= 2) {
                if (ig <= 1) {
                  if (ig <= 0) {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(0.00000, 0.00000, 0.00877);
                          } else {
                            return vec3(-0.03627, -0.00113, -0.01011);
                          }
                        } else {
                          return vec3(-0.08911, 0.00000, -0.03316);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.07680, 0.00000, -0.03520);
                        } else {
                          return vec3(-0.03328, 0.00000, 0.02026);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.00499, 0.00000, 0.01811);
                        } else {
                          return vec3(-0.00983, 0.00000, 0.13168);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.00000, 0.00000, -0.02953);
                        } else {
                          return vec3(0.00000, 0.00000, -0.03321);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(0.00000, 0.02767, -0.01447);
                          } else {
                            return vec3(0.00311, 0.01114, -0.00309);
                          }
                        } else {
                          return vec3(0.00000, 0.03398, 0.00069);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(0.00000, 0.00000, 0.01288);
                        } else {
                          return vec3(0.00000, 0.00000, 0.02267);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(0.00000, 0.00000, 0.00018);
                        } else {
                          return vec3(0.00000, 0.01075, 0.11100);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.00000, 0.05098, -0.01259);
                        } else {
                          return vec3(0.00000, 0.14661, 0.00878);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, -0.02014, -0.06724);
                        } else {
                          return vec3(0.00000, -0.02606, 0.03187);
                        }
                      } else {
                        return vec3(0.00000, -0.03384, -0.03685);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.05387, -0.04407);
                      } else {
                        return vec3(0.00000, -0.03780, -0.06088);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.07030, -0.09743);
                      } else {
                        return vec3(0.00000, -0.05559, 0.00575);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.08738, -0.03697);
                      } else {
                        return vec3(0.00000, 0.01558, 0.02559);
                      }
                    }
                  }
                }
              } else {
                if (ig <= 3) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, 0.03531, -0.02743);
                        } else {
                          return vec3(0.00000, 0.04396, 0.09812);
                        }
                      } else {
                        return vec3(0.00000, 0.05105, 0.05982);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.03872, 0.04809);
                      } else {
                        return vec3(0.00000, 0.06588, 0.02700);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.02276, -0.02552);
                      } else {
                        return vec3(0.00000, 0.02170, 0.04621);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.01845, 0.00880);
                      } else {
                        return vec3(0.00000, 0.08617, 0.01527);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, 0.03676, -0.00106);
                        } else {
                          return vec3(0.00000, 0.06413, 0.11233);
                        }
                      } else {
                        return vec3(0.00000, 0.09365, 0.08992);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.09722, 0.10708);
                      } else {
                        return vec3(0.00000, 0.09822, 0.03122);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.03762, -0.00523);
                      } else {
                        return vec3(-0.00551, 0.01982, 0.05264);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.08842, -0.03768, 0.04019);
                      } else {
                        return vec3(-0.00609, 0.06366, 0.00000);
                      }
                    }
                  }
                }
              }
            } else {
              if (ig <= 6) {
                if (ig <= 5) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00567, -0.09676, -0.06454);
                        } else {
                          return vec3(-0.01816, -0.06801, 0.00166);
                        }
                      } else {
                        return vec3(-0.01150, -0.01872, -0.02397);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00377, 0.02255, 0.04578);
                      } else {
                        return vec3(0.02743, 0.02696, -0.00419);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.01453, -0.08590, -0.14053);
                      } else {
                        return vec3(-0.06920, -0.12037, -0.06091);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.23768, -0.18291, 0.00000);
                      } else {
                        return vec3(-0.17220, -0.07434, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.02905, -0.01889, -0.03567);
                        } else {
                          return vec3(0.01037, -0.00181, -0.00287);
                        }
                      } else {
                        return vec3(0.02609, 0.04844, -0.03870);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.04740, 0.10601, 0.05466);
                      } else {
                        return vec3(0.05963, 0.12750, 0.04023);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02313, 0.03279, -0.03096);
                      } else {
                        return vec3(0.00263, -0.00384, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.17109, -0.06584, 0.00000);
                      } else {
                        return vec3(-0.09807, 0.03746, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ig <= 7) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.03577, -0.05229, -0.02389);
                        } else {
                          return vec3(-0.01200, -0.05054, -0.04570);
                        }
                      } else {
                        return vec3(0.03669, -0.01033, -0.12291);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.06082, 0.04423, -0.03049);
                      } else {
                        return vec3(0.05923, 0.08952, -0.00001);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02547, 0.04735, 0.00000);
                      } else {
                        return vec3(-0.04316, 0.01569, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.04106, 0.00000, 0.00000);
                      } else {
                        return vec3(0.13970, 0.08656, 0.01267);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.15035, 0.00765, 0.10577);
                        } else {
                          return vec3(-0.08380, -0.00512, 0.04146);
                        }
                      } else {
                        return vec3(0.01754, 0.02548, -0.07111);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.05446, 0.04254, 0.01404);
                      } else {
                        return vec3(0.07654, 0.05308, 0.07108);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.01371, 0.02327, 0.10531);
                      } else {
                        return vec3(0.00970, 0.00915, 0.10888);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.16710, 0.06083, 0.13829);
                      } else {
                        return vec3(0.26052, 0.20298, 0.15147);
                      }
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 4) {
              if (ig <= 2) {
                if (ig <= 1) {
                  if (ig <= 0) {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(0.06947, 0.02964, 0.02740);
                          } else {
                            return vec3(-0.03753, -0.04004, -0.03039);
                          }
                        } else {
                          return vec3(-0.08845, 0.00000, -0.06606);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.06674, 0.00000, -0.02935);
                        } else {
                          return vec3(-0.00605, 0.00000, 0.05653);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(0.00000, 0.00000, 0.05327);
                        } else {
                          return vec3(0.00000, 0.00000, 0.13893);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.00776, 0.00000, -0.01084);
                        } else {
                          return vec3(0.00000, 0.00000, -0.01189);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(0.20897, 0.09798, -0.00983);
                          } else {
                            return vec3(-0.06404, -0.03376, 0.00371);
                          }
                        } else {
                          return vec3(-0.04602, 0.00462, -0.02733);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.02089, -0.01985, -0.01022);
                        } else {
                          return vec3(0.00000, 0.00000, -0.01100);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(0.00000, 0.00000, -0.03151);
                        } else {
                          return vec3(0.00000, 0.01311, 0.09038);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.00000, -0.01751, -0.01838);
                        } else {
                          return vec3(0.00000, 0.06259, 0.00571);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.12357, 0.03937, -0.03582);
                        } else {
                          return vec3(0.00928, -0.05504, -0.01569);
                        }
                      } else {
                        return vec3(0.07588, 0.01019, 0.01264);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.05595, -0.06088);
                      } else {
                        return vec3(0.00000, -0.13443, -0.19097);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.13285, -0.16693);
                      } else {
                        return vec3(0.00000, -0.06904, 0.00766);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.02487, -0.09530, -0.01295);
                      } else {
                        return vec3(0.00000, -0.00132, 0.04023);
                      }
                    }
                  }
                }
              } else {
                if (ig <= 3) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.10029, 0.06715, -0.05089);
                        } else {
                          return vec3(-0.00618, 0.00966, 0.03690);
                        }
                      } else {
                        return vec3(0.06245, 0.07991, 0.12142);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.02367, 0.09861, 0.14151);
                      } else {
                        return vec3(0.00000, -0.01593, -0.08094);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.03594, -0.10218);
                      } else {
                        return vec3(0.00000, 0.03753, 0.06493);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.07466, 0.00898, 0.04795);
                      } else {
                        return vec3(0.02713, 0.10174, 0.03213);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.09954, 0.06003, -0.07675);
                        } else {
                          return vec3(-0.02223, 0.03673, 0.07570);
                        }
                      } else {
                        return vec3(0.02521, 0.11954, 0.17084);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.06059, 0.21258, 0.30626);
                      } else {
                        return vec3(0.06005, 0.14513, 0.12603);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.03402, 0.04629, 0.00367);
                      } else {
                        return vec3(0.01594, 0.07416, 0.09077);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06038, 0.02436, 0.07943);
                      } else {
                        return vec3(0.03564, 0.10895, 0.01420);
                      }
                    }
                  }
                }
              }
            } else {
              if (ig <= 6) {
                if (ig <= 5) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.06780, -0.06472, -0.10559);
                        } else {
                          return vec3(-0.04535, -0.07453, 0.00319);
                        }
                      } else {
                        return vec3(-0.01142, -0.02184, 0.01822);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.01390, 0.04162, 0.13672);
                      } else {
                        return vec3(0.05142, 0.05267, 0.08169);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.04411, -0.04742, -0.08224);
                      } else {
                        return vec3(0.00586, -0.04613, -0.02189);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.14619, -0.10359, 0.00000);
                      } else {
                        return vec3(-0.06866, -0.01182, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.08605, 0.01789, -0.05003);
                        } else {
                          return vec3(-0.01475, -0.00242, 0.01092);
                        }
                      } else {
                        return vec3(0.02224, 0.01726, -0.03526);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.04384, 0.04801, 0.05249);
                      } else {
                        return vec3(0.07919, 0.08157, 0.04384);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.06065, 0.03001, -0.04060);
                      } else {
                        return vec3(0.07494, 0.03885, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.09162, -0.01478, 0.00000);
                      } else {
                        return vec3(-0.01655, 0.05940, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ig <= 7) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.02220, -0.02163, -0.02225);
                        } else {
                          return vec3(-0.04333, -0.05640, -0.03176);
                        }
                      } else {
                        return vec3(0.03267, -0.04158, -0.13192);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.05858, -0.01256, -0.05277);
                      } else {
                        return vec3(0.07983, 0.03246, -0.03416);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00571, 0.02632, -0.01240);
                      } else {
                        return vec3(0.00583, 0.02786, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.04681, 0.00000, 0.00000);
                      } else {
                        return vec3(0.13967, 0.05981, 0.01371);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.09267, 0.02526, 0.10747);
                        } else {
                          return vec3(-0.11727, -0.01815, 0.04835);
                        }
                      } else {
                        return vec3(0.01802, 0.00158, -0.08638);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.05857, 0.03648, -0.01006);
                      } else {
                        return vec3(0.09700, 0.06283, 0.02511);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02997, 0.03047, 0.10631);
                      } else {
                        return vec3(0.02749, 0.01271, 0.10515);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.12081, 0.03852, 0.12068);
                      } else {
                        return vec3(0.37347, 0.16163, 0.13052);
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.37871, 0.07619, -0.00425);
                        } else {
                          return vec3(0.11434, -0.02656, -0.05976);
                        }
                      } else {
                        return vec3(-0.14041, -0.07471, -0.15434);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.09875, -0.06064, -0.07718);
                      } else {
                        return vec3(0.00000, 0.00000, 0.00394);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.00000, 0.00111);
                      } else {
                        return vec3(0.00000, 0.00000, 0.07313);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06205, -0.01835, -0.01683);
                      } else {
                        return vec3(-0.05822, 0.00000, 0.01466);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.23485, 0.09650, 0.00000);
                        } else {
                          return vec3(0.03785, 0.02733, 0.04354);
                        }
                      } else {
                        return vec3(-0.16333, -0.06763, -0.04265);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.11528, -0.07056, -0.02517);
                      } else {
                        return vec3(-0.00376, -0.04304, -0.03615);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.03135, -0.06369);
                      } else {
                        return vec3(0.00000, -0.00590, 0.05408);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06204, -0.03198, 0.00003);
                      } else {
                        return vec3(-0.04963, 0.03726, 0.05616);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.05912, 0.04802, 0.00000);
                      } else {
                        return vec3(-0.10278, -0.02878, -0.02917);
                      }
                    } else {
                      return vec3(0.04158, 0.03274, 0.06664);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03568, -0.01938, 0.02403);
                    } else {
                      return vec3(-0.05609, -0.16084, -0.16958);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03773, -0.18280, -0.19413);
                    } else {
                      return vec3(-0.06818, -0.11034, -0.01284);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.18939, -0.17016, -0.04413);
                    } else {
                      return vec3(-0.11129, -0.10422, 0.01005);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.02967, 0.10938, 0.00000);
                      } else {
                        return vec3(-0.08165, 0.04797, -0.00199);
                      }
                    } else {
                      return vec3(-0.05624, -0.00622, 0.04756);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.08673, 0.22060, 0.32358);
                    } else {
                      return vec3(-0.07499, -0.10269, -0.13762);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.07422, -0.07116, -0.12313);
                    } else {
                      return vec3(-0.06789, 0.04292, 0.08419);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.11248, -0.02264, 0.03756);
                    } else {
                      return vec3(0.00121, 0.03833, 0.00457);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.04326, 0.12970, 0.00000);
                      } else {
                        return vec3(-0.09829, 0.04749, 0.05867);
                      }
                    } else {
                      return vec3(-0.10669, 0.06873, 0.18425);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02089, 0.44001, 0.64492);
                    } else {
                      return vec3(0.01619, 0.17438, 0.24131);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02589, 0.11127, 0.09831);
                    } else {
                      return vec3(-0.01787, 0.15042, 0.16696);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.07074, 0.05449, 0.08321);
                    } else {
                      return vec3(0.03038, 0.09123, 0.00000);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.03116, 0.01354, -0.06078);
                      } else {
                        return vec3(-0.09848, -0.03641, 0.05359);
                      }
                    } else {
                      return vec3(-0.13246, -0.01536, 0.09835);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.10435, 0.02458, 0.21646);
                    } else {
                      return vec3(-0.03865, 0.02707, 0.14520);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.07103, 0.00195, 0.03051);
                    } else {
                      return vec3(-0.02140, 0.07707, 0.08585);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.16041, -0.02443, 0.00519);
                    } else {
                      return vec3(-0.12981, 0.00361, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.05123, 0.08890, 0.00785);
                      } else {
                        return vec3(-0.06198, 0.03989, 0.08518);
                      }
                    } else {
                      return vec3(-0.09809, 0.03073, 0.05649);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07605, 0.02272, 0.12357);
                    } else {
                      return vec3(-0.00452, 0.03407, 0.08026);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02117, 0.03483, 0.00978);
                    } else {
                      return vec3(0.02844, 0.10512, 0.07200);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.14857, 0.00000, 0.00000);
                    } else {
                      return vec3(-0.11635, 0.00699, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00296, 0.02845, 0.04416);
                      } else {
                        return vec3(-0.07220, -0.02583, 0.04619);
                      }
                    } else {
                      return vec3(-0.08388, -0.03227, -0.05228);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05687, -0.02413, 0.01106);
                    } else {
                      return vec3(0.00417, 0.01270, -0.00861);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.06959, 0.00758, -0.02959);
                    } else {
                      return vec3(-0.06541, 0.05127, 0.03434);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.15522, 0.00000, 0.00000);
                    } else {
                      return vec3(-0.10413, 0.00000, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.10844, 0.05122, 0.15812);
                      } else {
                        return vec3(-0.13082, -0.00460, 0.10655);
                      }
                    } else {
                      return vec3(-0.09205, 0.00176, -0.03378);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05090, 0.02447, 0.02687);
                    } else {
                      return vec3(0.02025, 0.06324, 0.01405);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.06889, 0.04121, 0.02635);
                    } else {
                      return vec3(-0.08786, 0.01178, 0.07866);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.15544, 0.00000, 0.05151);
                    } else {
                      return vec3(0.00858, 0.03760, 0.04905);
                    }
                  }
                }
              }
            }
          }
        }
      } else {
        if (ir <= 3) {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.42882, 0.00770, -0.03081);
                        } else {
                          return vec3(0.17545, -0.02923, -0.07414);
                        }
                      } else {
                        return vec3(-0.06995, -0.07071, -0.10276);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.13614, -0.07137, -0.02588);
                      } else {
                        return vec3(-0.02640, -0.02828, 0.01576);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.00000, -0.00058);
                      } else {
                        return vec3(0.00000, 0.00000, 0.05925);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.09487, -0.03946, -0.03096);
                      } else {
                        return vec3(-0.10244, -0.01402, -0.01028);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.10754, 0.00000, -0.00409);
                        } else {
                          return vec3(0.09528, 0.03097, 0.02070);
                        }
                      } else {
                        return vec3(0.03200, 0.00845, -0.01700);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.16862, 0.00287, 0.04786);
                      } else {
                        return vec3(-0.04617, 0.02222, 0.04204);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.02304, -0.01446);
                      } else {
                        return vec3(-0.00024, 0.02035, 0.06111);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.10012, -0.02202, -0.00856);
                      } else {
                        return vec3(-0.05890, 0.03196, 0.03725);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.09246, -0.02146, 0.00000);
                      } else {
                        return vec3(0.05287, -0.01843, -0.01096);
                      }
                    } else {
                      return vec3(0.08034, -0.00512, -0.01089);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07495, 0.00594, 0.07297);
                    } else {
                      return vec3(-0.13251, -0.05002, 0.00493);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.09395, -0.09492, -0.08237);
                    } else {
                      return vec3(-0.09588, -0.06669, 0.02556);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.13555, -0.13854, -0.03287);
                    } else {
                      return vec3(-0.03613, -0.07926, 0.02289);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01345, 0.08529, 0.00000);
                      } else {
                        return vec3(0.04988, 0.10330, -0.01561);
                      }
                    } else {
                      return vec3(0.03476, 0.04643, -0.06047);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00169, -0.03428, -0.00134);
                    } else {
                      return vec3(-0.10300, -0.03635, -0.02300);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.09070, 0.00341, -0.02702);
                    } else {
                      return vec3(-0.02662, 0.07861, 0.11281);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.03152, 0.00181, 0.03595);
                    } else {
                      return vec3(0.11455, 0.05210, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.08892, 0.15005, 0.00000);
                      } else {
                        return vec3(-0.01327, 0.10892, -0.00965);
                      }
                    } else {
                      return vec3(-0.06613, 0.03904, -0.01642);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05290, 0.01325, 0.07528);
                    } else {
                      return vec3(-0.03830, 0.03813, 0.07491);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02763, 0.12833, 0.10411);
                    } else {
                      return vec3(0.01816, 0.22192, 0.22382);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.05394, 0.10547, 0.06510);
                    } else {
                      return vec3(0.18136, 0.11136, 0.00000);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.10323, 0.04664, -0.02904);
                      } else {
                        return vec3(-0.02855, -0.01442, -0.01597);
                      }
                    } else {
                      return vec3(-0.08230, -0.04069, -0.00746);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.08127, -0.05595, 0.10374);
                    } else {
                      return vec3(-0.02671, -0.04505, 0.04245);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08343, 0.01555, 0.03370);
                    } else {
                      return vec3(0.01243, 0.18771, 0.14566);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00826, 0.04503, 0.00000);
                    } else {
                      return vec3(0.01529, 0.03174, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.12142, 0.11563, -0.02896);
                      } else {
                        return vec3(-0.00001, 0.04858, 0.03356);
                      }
                    } else {
                      return vec3(-0.04872, 0.02357, 0.01547);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.04558, 0.00638, 0.10553);
                    } else {
                      return vec3(0.02374, 0.00833, 0.04964);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02900, 0.02387, -0.01080);
                    } else {
                      return vec3(0.14629, 0.14181, 0.08153);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00185, 0.00000, 0.00000);
                    } else {
                      return vec3(0.00952, 0.00000, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.07368, 0.04830, 0.00609);
                      } else {
                        return vec3(0.00172, -0.01725, 0.01386);
                      }
                    } else {
                      return vec3(-0.01824, -0.03364, -0.07157);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01808, -0.03750, 0.00171);
                    } else {
                      return vec3(0.03113, -0.01756, -0.03154);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02668, -0.03442, -0.07274);
                    } else {
                      return vec3(0.01529, 0.03276, 0.02288);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.08955, 0.00000, 0.00000);
                    } else {
                      return vec3(-0.03999, 0.00000, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.02314, 0.06941, 0.12009);
                      } else {
                        return vec3(-0.04680, 0.00449, 0.08367);
                      }
                    } else {
                      return vec3(-0.01678, -0.00139, -0.04529);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00510, 0.00541, 0.01699);
                    } else {
                      return vec3(0.05210, 0.02944, -0.01493);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.04913, -0.00628, -0.03542);
                    } else {
                      return vec3(-0.07060, 0.01264, 0.05832);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.16132, 0.00000, 0.02746);
                    } else {
                      return vec3(0.00914, 0.00000, 0.01965);
                    }
                  }
                }
              }
            }
          }
        } else {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.31522, 0.00000, -0.03332);
                        } else {
                          return vec3(0.19639, -0.02621, -0.07724);
                        }
                      } else {
                        return vec3(0.08419, -0.06047, -0.05698);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00325, -0.04896, 0.02441);
                      } else {
                        return vec3(0.06975, -0.00788, 0.04040);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.08789, 0.02355, 0.01586);
                      } else {
                        return vec3(0.06829, 0.00033, 0.06883);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.05833, -0.04391, -0.03588);
                      } else {
                        return vec3(-0.09239, -0.01800, -0.03691);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.01942, 0.00000, -0.00523);
                        } else {
                          return vec3(-0.02450, -0.05150, -0.01124);
                        }
                      } else {
                        return vec3(0.15992, 0.01929, -0.01039);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.07793, 0.07733, 0.11035);
                      } else {
                        return vec3(0.07566, 0.11216, 0.13860);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.09382, 0.09729, 0.05958);
                      } else {
                        return vec3(0.09658, 0.06057, 0.08675);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.02423, -0.00753, -0.01782);
                      } else {
                        return vec3(0.05876, 0.02676, 0.00295);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.21852, -0.08323, 0.00000);
                      } else {
                        return vec3(-0.04298, -0.08954, 0.01032);
                      }
                    } else {
                      return vec3(0.26970, 0.01482, -0.01611);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.07483, 0.05951, 0.15725);
                    } else {
                      return vec3(-0.02473, 0.09816, 0.20956);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00999, 0.00181, 0.03285);
                    } else {
                      return vec3(0.01996, -0.02971, 0.05319);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02088, -0.12835, -0.04625);
                    } else {
                      return vec3(0.07912, -0.08294, -0.00961);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.05400, 0.01188, 0.00000);
                      } else {
                        return vec3(0.25913, 0.09498, -0.01116);
                      }
                    } else {
                      return vec3(0.37577, 0.09615, -0.07322);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.18612, 0.04307, 0.12195);
                    } else {
                      return vec3(-0.04618, 0.00897, 0.06878);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.01752, 0.02743, 0.00894);
                    } else {
                      return vec3(0.06917, 0.08406, 0.10779);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08349, 0.00620, 0.01887);
                    } else {
                      return vec3(0.22993, 0.05500, 0.00236);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.13641, 0.10743, 0.00000);
                      } else {
                        return vec3(0.17090, 0.12879, -0.03211);
                      }
                    } else {
                      return vec3(0.13372, 0.09836, -0.13841);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04743, -0.01735, -0.06156);
                    } else {
                      return vec3(-0.03065, -0.06947, -0.07343);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08625, -0.00364, -0.02644);
                    } else {
                      return vec3(0.16155, 0.19108, 0.16867);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.19604, 0.10528, 0.06080);
                    } else {
                      return vec3(0.29985, 0.11560, 0.00000);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.19507, 0.03042, -0.02057);
                      } else {
                        return vec3(0.08578, -0.00853, -0.10697);
                      }
                    } else {
                      return vec3(0.04728, -0.00561, -0.17759);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04416, -0.01220, -0.07211);
                    } else {
                      return vec3(0.07859, 0.01089, -0.10538);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00350, -0.06349, -0.06781);
                    } else {
                      return vec3(0.37891, 0.20815, 0.14228);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.15415, 0.04821, 0.00000);
                    } else {
                      return vec3(0.12592, 0.03541, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.22717, 0.11535, -0.04462);
                      } else {
                        return vec3(0.10865, 0.05474, -0.05466);
                      }
                    } else {
                      return vec3(0.06612, 0.03994, -0.09793);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.06992, 0.04063, 0.03037);
                    } else {
                      return vec3(0.10578, 0.05002, -0.00380);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.10589, -0.01990, -0.06122);
                    } else {
                      return vec3(0.33975, 0.13941, 0.06880);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.16045, 0.00000, 0.00000);
                    } else {
                      return vec3(0.12512, 0.00000, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.19206, 0.06075, -0.05309);
                      } else {
                        return vec3(0.12030, -0.00164, -0.05213);
                      }
                    } else {
                      return vec3(0.09867, -0.01340, -0.13304);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.08383, -0.02180, -0.04551);
                    } else {
                      return vec3(0.08724, -0.04206, -0.07606);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00301, -0.09481, -0.12290);
                    } else {
                      return vec3(0.08628, -0.00929, -0.02087);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01242, 0.00000, 0.00000);
                    } else {
                      return vec3(0.06783, 0.00000, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.10783, 0.09565, 0.05584);
                      } else {
                        return vec3(0.07474, 0.02614, 0.03888);
                      }
                    } else {
                      return vec3(0.09047, 0.01054, -0.07530);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.08070, -0.00177, -0.00987);
                    } else {
                      return vec3(0.11624, 0.00677, -0.04849);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00524, -0.04707, -0.08257);
                    } else {
                      return vec3(-0.03703, -0.04499, -0.00528);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.11560, 0.00000, 0.02259);
                    } else {
                      return vec3(0.08533, 0.00000, 0.01354);
                    }
                  }
                }
              }
            }
          }
        }
      }
    } else {
      if (ir <= 6) {
        if (ir <= 5) {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.08618, 0.00000, -0.03531);
                        } else {
                          return vec3(0.02330, 0.00000, -0.09337);
                        }
                      } else {
                        return vec3(-0.00316, -0.04416, -0.08075);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01615, -0.00755, 0.01572);
                      } else {
                        return vec3(0.02217, 0.00784, 0.02946);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02227, -0.05582, -0.05314);
                      } else {
                        return vec3(-0.01938, -0.07414, -0.00500);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.12464, -0.09392, -0.06170);
                      } else {
                        return vec3(-0.15986, -0.04797, -0.02585);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.09301, 0.00000, -0.01033);
                        } else {
                          return vec3(-0.23361, -0.01649, -0.02141);
                        }
                      } else {
                        return vec3(-0.04748, 0.00232, -0.02161);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.01570, 0.10618, 0.11168);
                      } else {
                        return vec3(0.01794, 0.13907, 0.14449);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00593, 0.05007, 0.02350);
                      } else {
                        return vec3(-0.00406, 0.02022, 0.03666);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.04290, -0.00802, -0.04587);
                      } else {
                        return vec3(-0.01388, 0.02940, -0.00348);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.20687, -0.00009, 0.00000);
                      } else {
                        return vec3(-0.37706, -0.12830, 0.00000);
                      }
                    } else {
                      return vec3(-0.10989, -0.04590, 0.03660);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07652, 0.07850, 0.21738);
                    } else {
                      return vec3(-0.15213, 0.12084, 0.26716);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.15405, -0.00352, 0.07761);
                    } else {
                      return vec3(-0.12161, -0.02868, 0.07117);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.11884, -0.09032, -0.04390);
                    } else {
                      return vec3(-0.03323, -0.04734, -0.00119);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.12754, 0.03992, 0.00000);
                      } else {
                        return vec3(0.03955, 0.04513, 0.00000);
                      }
                    } else {
                      return vec3(0.18917, 0.07540, -0.05790);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.14662, -0.01646, 0.13279);
                    } else {
                      return vec3(-0.20404, 0.03906, 0.17445);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.17300, 0.01036, 0.06060);
                    } else {
                      return vec3(-0.08746, 0.06210, 0.11806);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.04592, 0.02572, 0.01972);
                    } else {
                      return vec3(0.07047, 0.08529, 0.06709);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01857, 0.09750, 0.00000);
                      } else {
                        return vec3(-0.03187, 0.05938, 0.00000);
                      }
                    } else {
                      return vec3(0.00548, 0.04834, -0.09409);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.26705, -0.16499, -0.03383);
                    } else {
                      return vec3(-0.20387, -0.07610, 0.00933);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.14844, -0.00875, 0.02918);
                    } else {
                      return vec3(-0.00619, 0.11538, 0.15675);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02689, 0.07744, 0.05958);
                    } else {
                      return vec3(0.11014, 0.12652, 0.02502);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.06003, 0.00894, 0.00000);
                      } else {
                        return vec3(-0.13422, -0.02797, 0.00000);
                      }
                    } else {
                      return vec3(-0.14699, -0.01841, -0.13333);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.15599, -0.02531, -0.04825);
                    } else {
                      return vec3(-0.11674, -0.02851, 0.01679);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03346, 0.00750, -0.00405);
                    } else {
                      return vec3(0.22818, 0.14888, 0.13480);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.14186, 0.03755, 0.00000);
                    } else {
                      return vec3(0.12609, 0.04576, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.02313, 0.12487, 0.00000);
                      } else {
                        return vec3(-0.05435, 0.08115, 0.01366);
                      }
                    } else {
                      return vec3(-0.08583, 0.07904, -0.04812);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07802, 0.10029, 0.06417);
                    } else {
                      return vec3(-0.07658, 0.09354, 0.13046);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03853, 0.05671, 0.02319);
                    } else {
                      return vec3(0.24339, 0.20386, 0.17203);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.15710, 0.06667, 0.00000);
                    } else {
                      return vec3(0.12275, 0.02408, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.06171, 0.07471, 0.00000);
                      } else {
                        return vec3(0.02110, 0.01888, 0.00570);
                      }
                    } else {
                      return vec3(0.01511, 0.01256, -0.05993);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00549, 0.00882, 0.03911);
                    } else {
                      return vec3(-0.03159, 0.00528, 0.03996);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03572, -0.00952, -0.06508);
                    } else {
                      return vec3(0.00410, 0.02355, 0.00846);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.08384, -0.00282, -0.00462);
                    } else {
                      return vec3(-0.01604, 0.00000, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.01605, 0.07660, 0.06421);
                      } else {
                        return vec3(0.00097, 0.02300, 0.07489);
                      }
                    } else {
                      return vec3(0.02498, 0.00164, -0.00011);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00461, -0.01592, 0.08152);
                    } else {
                      return vec3(-0.00719, 0.00705, 0.05313);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00430, 0.03682, -0.05633);
                    } else {
                      return vec3(-0.03589, 0.00973, -0.00426);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.21127, -0.01700, -0.01670);
                    } else {
                      return vec3(-0.08959, 0.00000, 0.00000);
                    }
                  }
                }
              }
            }
          }
        } else {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.10221, 0.00000, -0.02703);
                        } else {
                          return vec3(0.04358, 0.00000, -0.08745);
                        }
                      } else {
                        return vec3(0.06471, -0.04330, -0.11791);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.10471, -0.02710, -0.00820);
                      } else {
                        return vec3(0.16026, 0.00866, 0.02027);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.15359, -0.04174, -0.05489);
                      } else {
                        return vec3(0.09990, -0.07660, -0.01949);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00546, -0.07989, -0.07177);
                      } else {
                        return vec3(-0.02796, -0.04531, -0.03155);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.09811, 0.00000, -0.00687);
                        } else {
                          return vec3(-0.07234, -0.01471, -0.01763);
                        }
                      } else {
                        return vec3(0.06095, -0.01181, -0.05295);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.13166, 0.07033, 0.06283);
                      } else {
                        return vec3(0.17393, 0.10809, 0.08380);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.16145, 0.04701, -0.01298);
                      } else {
                        return vec3(0.12507, 0.01385, 0.01197);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.08161, -0.00158, -0.06595);
                      } else {
                        return vec3(0.09430, 0.03433, -0.02574);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.03771, 0.00000, 0.00000);
                      } else {
                        return vec3(0.02775, -0.03131, 0.00000);
                      }
                    } else {
                      return vec3(0.03043, -0.02739, 0.03168);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03087, 0.02703, 0.14050);
                    } else {
                      return vec3(0.04487, 0.04856, 0.13343);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02906, -0.01731, 0.01738);
                    } else {
                      return vec3(0.01590, -0.03816, 0.04279);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00399, -0.09688, -0.07482);
                    } else {
                      return vec3(0.04161, -0.06524, -0.03790);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.05422, 0.04665, 0.00000);
                      } else {
                        return vec3(0.14370, 0.02277, 0.00000);
                      }
                    } else {
                      return vec3(0.22419, 0.07359, 0.00190);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04609, 0.02224, 0.07889);
                    } else {
                      return vec3(0.00847, 0.02985, 0.09582);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03437, 0.01344, 0.01585);
                    } else {
                      return vec3(0.04872, 0.03421, 0.07394);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03528, -0.01144, -0.03034);
                    } else {
                      return vec3(0.09100, 0.03851, 0.02172);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.09401, 0.08361, 0.00000);
                      } else {
                        return vec3(-0.13543, -0.09358, 0.00000);
                      }
                    } else {
                      return vec3(0.07491, -0.00558, -0.09167);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07115, -0.12463, -0.05570);
                    } else {
                      return vec3(0.01142, 0.00883, 0.06396);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06083, 0.00298, -0.00540);
                    } else {
                      return vec3(0.06118, 0.04509, 0.08328);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02508, -0.00358, -0.01112);
                    } else {
                      return vec3(0.07603, 0.06073, 0.03850);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00811, -0.02667, 0.00000);
                      } else {
                        return vec3(-0.03970, -0.05501, 0.00000);
                      }
                    } else {
                      return vec3(0.04699, 0.07302, -0.13329);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01307, -0.04220, -0.10491);
                    } else {
                      return vec3(0.07576, -0.01568, 0.02832);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.09770, -0.04837, -0.09453);
                    } else {
                      return vec3(0.07791, -0.00703, 0.01908);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00713, -0.09770, -0.08591);
                    } else {
                      return vec3(0.05815, -0.01662, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.08061, 0.11229, 0.00000);
                      } else {
                        return vec3(0.04099, 0.11411, 0.01340);
                      }
                    } else {
                      return vec3(0.02537, 0.13575, -0.06591);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04575, 0.13745, 0.01058);
                    } else {
                      return vec3(0.05981, 0.10289, 0.06377);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.07933, 0.03462, -0.04337);
                    } else {
                      return vec3(-0.10162, -0.08343, -0.09405);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00783, -0.05182, -0.09768);
                    } else {
                      return vec3(0.12222, 0.04311, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.14585, 0.08460, 0.00000);
                      } else {
                        return vec3(0.11177, 0.04568, -0.02208);
                      }
                    } else {
                      return vec3(0.10871, 0.04621, -0.09646);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.09622, 0.04987, -0.00933);
                    } else {
                      return vec3(0.08245, 0.05616, 0.00067);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06101, 0.03333, -0.08526);
                    } else {
                      return vec3(0.01606, -0.00086, -0.04697);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.07713, -0.03666, -0.03326);
                    } else {
                      return vec3(-0.03630, 0.00000, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.10769, 0.06784, 0.01282);
                      } else {
                        return vec3(0.08646, 0.01321, 0.02539);
                      }
                    } else {
                      return vec3(0.10754, 0.02070, -0.04131);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.07214, 0.01209, 0.05090);
                    } else {
                      return vec3(0.05951, 0.03841, 0.03374);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06328, 0.06541, -0.06066);
                    } else {
                      return vec3(0.07839, 0.05404, -0.00200);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.13296, -0.03372, -0.03694);
                    } else {
                      return vec3(-0.06166, 0.00000, 0.00000);
                    }
                  }
                }
              }
            }
          }
        }
      } else {
        if (ir <= 7) {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.09233, 0.00000, 0.00000);
                        } else {
                          return vec3(0.00818, 0.00000, -0.04275);
                        }
                      } else {
                        return vec3(0.00851, -0.05984, -0.15121);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.04850, -0.06386, -0.03837);
                      } else {
                        return vec3(0.09656, -0.03290, 0.00568);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.08794, -0.02555, -0.02783);
                      } else {
                        return vec3(0.03290, -0.04756, 0.02326);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.01166, -0.06669, -0.03076);
                      } else {
                        return vec3(0.00339, 0.00129, 0.03640);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.21117, 0.00000, 0.00000);
                        } else {
                          return vec3(-0.01393, -0.02978, 0.00000);
                        }
                      } else {
                        return vec3(0.06381, -0.04356, -0.09529);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.09399, 0.00504, 0.00117);
                      } else {
                        return vec3(0.14286, 0.05196, 0.01994);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.14559, 0.05498, -0.03436);
                      } else {
                        return vec3(0.09486, 0.03774, 0.01834);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.08186, 0.00881, -0.05277);
                      } else {
                        return vec3(0.12088, 0.07521, 0.00886);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.23548, 0.05222, 0.00000);
                      } else {
                        return vec3(0.17669, 0.01906, -0.00205);
                      }
                    } else {
                      return vec3(0.03747, -0.03941, 0.00519);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00173, -0.03246, 0.07817);
                    } else {
                      return vec3(0.05755, -0.00072, 0.05165);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.07140, -0.00917, -0.03677);
                    } else {
                      return vec3(0.02335, -0.02280, 0.01805);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01557, -0.08799, -0.08305);
                    } else {
                      return vec3(0.06722, -0.03838, -0.03469);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.22959, 0.10119, 0.00000);
                      } else {
                        return vec3(0.22656, 0.10015, -0.00042);
                      }
                    } else {
                      return vec3(0.10168, 0.06972, 0.02631);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.05326, 0.04315, 0.09411);
                    } else {
                      return vec3(0.06734, 0.05285, 0.06628);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.08236, 0.03862, -0.02548);
                    } else {
                      return vec3(0.03560, 0.03619, 0.04175);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01645, -0.02685, -0.05071);
                    } else {
                      return vec3(0.06366, 0.03148, 0.01002);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.19413, 0.09971, 0.00000);
                      } else {
                        return vec3(0.11757, 0.03483, 0.00000);
                      }
                    } else {
                      return vec3(0.10296, 0.07782, 0.00039);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.09475, 0.10661, 0.08424);
                    } else {
                      return vec3(0.05472, 0.05611, 0.07220);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.05843, 0.02885, -0.02269);
                    } else {
                      return vec3(-0.00915, 0.02897, 0.05402);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.05685, -0.04453, -0.03206);
                    } else {
                      return vec3(-0.01231, 0.02272, 0.04383);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.08854, -0.04467, 0.00000);
                      } else {
                        return vec3(0.05710, -0.03069, 0.01290);
                      }
                    } else {
                      return vec3(0.07602, 0.12122, 0.05280);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.07452, 0.05561, -0.01980);
                    } else {
                      return vec3(0.08287, -0.03016, 0.03072);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06883, -0.00840, -0.02666);
                    } else {
                      return vec3(-0.04799, -0.04098, 0.03673);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.17078, -0.16153, -0.05486);
                    } else {
                      return vec3(-0.11984, -0.09083, 0.02292);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.11604, 0.08174, 0.00000);
                      } else {
                        return vec3(0.05735, 0.09799, 0.03208);
                      }
                    } else {
                      return vec3(0.01613, 0.12570, -0.01467);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01860, 0.11829, 0.03565);
                    } else {
                      return vec3(0.04377, 0.12261, 0.08675);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.08559, 0.09694, 0.03233);
                    } else {
                      return vec3(0.06292, 0.10716, 0.11834);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.15490, -0.07272, -0.01579);
                    } else {
                      return vec3(-0.08253, -0.00560, 0.00000);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.06640, 0.05181, 0.00000);
                      } else {
                        return vec3(0.03726, 0.01844, -0.01396);
                      }
                    } else {
                      return vec3(0.04299, 0.02652, -0.05940);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03296, 0.04219, 0.04018);
                    } else {
                      return vec3(0.03382, 0.06394, 0.05174);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02677, 0.05722, -0.00291);
                    } else {
                      return vec3(0.01266, 0.05910, 0.09787);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.07825, -0.03870, -0.00426);
                    } else {
                      return vec3(0.06699, 0.02141, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, 0.01343, -0.00671);
                      } else {
                        return vec3(0.03754, 0.00000, -0.02310);
                      }
                    } else {
                      return vec3(0.08447, 0.00000, -0.07060);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.05750, 0.00000, 0.01915);
                    } else {
                      return vec3(0.04650, 0.03224, 0.02831);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01855, 0.06668, -0.00720);
                    } else {
                      return vec3(0.04624, 0.06334, 0.07321);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.10622, 0.00585, 0.00884);
                    } else {
                      return vec3(0.16801, 0.00000, 0.01112);
                    }
                  }
                }
              }
            }
          }
        } else {
          if (ig <= 4) {
            if (ig <= 2) {
              if (ig <= 1) {
                if (ig <= 0) {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.07711, 0.00000, 0.00000);
                        } else {
                          return vec3(-0.15677, -0.06479, 0.00000);
                        }
                      } else {
                        return vec3(-0.15588, -0.16341, -0.06733);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.15497, -0.16106, -0.03504);
                      } else {
                        return vec3(-0.15741, -0.11851, 0.02225);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.11534, -0.04094, 0.04090);
                      } else {
                        return vec3(-0.13712, -0.00330, 0.12878);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.09874, 0.04042, 0.13908);
                      } else {
                        return vec3(-0.02415, 0.04798, 0.21382);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.14649, 0.00000, 0.00000);
                        } else {
                          return vec3(-0.01191, -0.13426, 0.00000);
                        }
                      } else {
                        return vec3(-0.01539, -0.17325, -0.10120);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.03636, -0.14038, -0.04203);
                      } else {
                        return vec3(-0.04333, -0.06186, -0.01792);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02545, 0.04174, -0.02941);
                      } else {
                        return vec3(-0.00368, 0.07365, 0.05559);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.05043, 0.10768, 0.05265);
                      } else {
                        return vec3(0.12619, 0.15964, 0.12803);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.23801, 0.03052, -0.03282);
                      } else {
                        return vec3(0.00000, -0.09291, -0.05904);
                      }
                    } else {
                      return vec3(0.00000, -0.19466, -0.07677);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.16971, -0.00238);
                    } else {
                      return vec3(0.00000, -0.09604, -0.03165);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06665, -0.01784, -0.10175);
                    } else {
                      return vec3(0.02316, -0.00326, -0.02976);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.07381, -0.00305, -0.05753);
                    } else {
                      return vec3(0.14430, 0.03500, 0.01602);
                    }
                  }
                }
              }
            } else {
              if (ig <= 3) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.23318, 0.09352, -0.04556);
                      } else {
                        return vec3(0.00948, 0.01863, -0.07808);
                      }
                    } else {
                      return vec3(0.00000, -0.04253, -0.01061);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.02681, 0.07918);
                    } else {
                      return vec3(0.00000, 0.01074, 0.02291);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.07495, 0.05022, -0.08520);
                    } else {
                      return vec3(0.02628, 0.04595, -0.02067);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.05299, 0.03416, -0.04648);
                    } else {
                      return vec3(0.10669, 0.07176, 0.03809);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.20717, 0.06403, -0.06279);
                      } else {
                        return vec3(0.02481, 0.08153, -0.03483);
                      }
                    } else {
                      return vec3(0.00000, 0.08940, 0.09184);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, 0.09152, 0.14932);
                    } else {
                      return vec3(0.00000, 0.06143, 0.07664);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02456, 0.06490, -0.06413);
                    } else {
                      return vec3(-0.01060, 0.04227, -0.00178);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02782, 0.00166, -0.03331);
                    } else {
                      return vec3(-0.00472, 0.02953, 0.05788);
                    }
                  }
                }
              }
            }
          } else {
            if (ig <= 6) {
              if (ig <= 5) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.11210, -0.12177, -0.09114);
                      } else {
                        return vec3(0.01392, -0.06091, -0.03921);
                      }
                    } else {
                      return vec3(0.00000, 0.02637, 0.11409);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, 0.02665, 0.13395);
                    } else {
                      return vec3(0.00000, -0.00496, 0.00578);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02499, 0.01824, -0.04250);
                    } else {
                      return vec3(-0.00627, -0.02654, 0.02532);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.11993, -0.12658, -0.01015);
                    } else {
                      return vec3(-0.16171, -0.13002, 0.07454);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.07628, -0.03448, -0.10026);
                      } else {
                        return vec3(0.00319, -0.01991, -0.07342);
                      }
                    } else {
                      return vec3(0.00000, 0.03382, -0.02769);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00694, 0.05954, 0.03506);
                    } else {
                      return vec3(0.00000, 0.09184, 0.03727);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02929, 0.05745, -0.05954);
                    } else {
                      return vec3(0.03107, 0.06204, 0.06587);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.09495, -0.04020, 0.05239);
                    } else {
                      return vec3(-0.14956, -0.05735, 0.11599);
                    }
                  }
                }
              }
            } else {
              if (ig <= 7) {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, -0.10080, -0.12280);
                      } else {
                        return vec3(0.00000, -0.06511, -0.14976);
                      }
                    } else {
                      return vec3(0.00000, -0.03074, -0.12818);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.01784, 0.08709);
                    } else {
                      return vec3(0.02094, 0.01984, 0.05775);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00397, -0.01222, -0.06527);
                    } else {
                      return vec3(0.02014, 0.02547, 0.11934);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.22273, 0.06063, 0.07185);
                    } else {
                      return vec3(0.23895, 0.03702, 0.11272);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, 0.00000, -0.11185);
                      } else {
                        return vec3(0.00000, 0.00000, -0.14860);
                      }
                    } else {
                      return vec3(0.00000, 0.00000, -0.15576);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, 0.00000, -0.11290);
                    } else {
                      return vec3(0.00551, 0.00000, -0.06422);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01264, 0.04650, 0.05350);
                    } else {
                      return vec3(0.01696, 0.06165, 0.19438);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.36187, 0.12940, 0.15473);
                    } else {
                      return vec3(0.76222, 0.21603, 0.11468);
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
}

vec3 msEvalTetra9(vec3 x) {
    vec3 s = clamp(x, 0.0, 1.0) * 8.0;
    vec3 i0f = clamp(floor(s), 0.0, 7.0);
    vec3 f = s - i0f;
    int r0 = int(i0f.r + 0.5);
    int g0 = int(i0f.g + 0.5);
    int b0 = int(i0f.b + 0.5);
    int r1 = r0 + 1;
    int g1 = g0 + 1;
    int b1 = b0 + 1;
    vec3 c000 = msLut9Node(r0, g0, b0);
    vec3 c100 = msLut9Node(r1, g0, b0);
    vec3 c010 = msLut9Node(r0, g1, b0);
    vec3 c110 = msLut9Node(r1, g1, b0);
    vec3 c001 = msLut9Node(r0, g0, b1);
    vec3 c101 = msLut9Node(r1, g0, b1);
    vec3 c011 = msLut9Node(r0, g1, b1);
    vec3 c111 = msLut9Node(r1, g1, b1);
    float fr = f.r;
    float fg = f.g;
    float fb = f.b;
    if (fr >= fg) {
        if (fg >= fb) {
            return c000 + fr * (c100 - c000) + fg * (c110 - c100) + fb * (c111 - c110);
        } else if (fr >= fb) {
            return c000 + fr * (c100 - c000) + fb * (c101 - c100) + fg * (c111 - c101);
        } else {
            return c000 + fb * (c001 - c000) + fr * (c101 - c001) + fg * (c111 - c101);
        }
    } else {
        if (fr >= fb) {
            return c000 + fg * (c010 - c000) + fr * (c110 - c010) + fb * (c111 - c110);
        } else if (fg >= fb) {
            return c000 + fg * (c010 - c000) + fb * (c011 - c010) + fr * (c111 - c011);
        } else {
            return c000 + fb * (c001 - c000) + fg * (c011 - c001) + fr * (c111 - c011);
        }
    }
}
vec3 msApplyColour(vec3 xIn) {
    vec3 x = clamp(xIn, 0.0, 1.0);
    vec3 c1d = vec3(msCurveR(x.r), msCurveG(x.g), msCurveB(x.b));
    vec3 u = 0.5 * x + 0.5 * c1d;
    float r = u.r;
    float g = u.g;
    float b = u.b;
    float rr = r * r;
    float gg = g * g;
    float bb = b * b;
    float rg = r * g;
    float rb = r * b;
    float gb = g * b;
    float rrr = rr * r;
    float ggg = gg * g;
    float bbb = bb * b;
    float rrg = rr * g;
    float rrb = rr * b;
    float ggr = gg * r;
    float ggb = gg * b;
    float bbr = bb * r;
    float bbg = bb * g;
    float rgb_p = r * g * b;
    float mx = max(max(r, g), b);
    float mn = min(min(r, g), b);
    float md = (r + g + b) - mx - mn;
    float ch = mx - mn;
    vec3 outCol = vec3(-0.040219, -0.022389, -0.001363);
    outCol += (r) * vec3(1.038657, 0.328738, -0.068369);
    outCol += (g) * vec3(-1.078282, -0.112306, 0.237462);
    outCol += (b) * vec3(1.695032, 0.817332, 0.258449);
    outCol += (rr) * vec3(-0.227333, -0.819733, 0.491372);
    outCol += (gg) * vec3(4.096398, 3.768893, 0.218725);
    outCol += (bb) * vec3(-8.468034, -4.796376, 0.645605);
    outCol += (rg) * vec3(3.173167, -2.014906, -3.930543);
    outCol += (rb) * vec3(-2.709546, 1.534256, 0.319593);
    outCol += (gb) * vec3(-3.223309, -0.144803, 3.036885);
    outCol += (rrr) * vec3(2.282794, 0.310264, -2.403026);
    outCol += (ggg) * vec3(-6.283164, -5.241821, 1.504194);
    outCol += (bbb) * vec3(10.319119, 8.776061, 1.583989);
    outCol += (rrg) * vec3(-2.085996, 2.216910, 3.385102);
    outCol += (rrb) * vec3(4.298427, 2.326692, 1.557103);
    outCol += (ggr) * vec3(0.107551, 1.847329, -0.774813);
    outCol += (ggb) * vec3(4.829390, 1.419856, -0.739304);
    outCol += (bbr) * vec3(5.056757, -2.811062, -2.438544);
    outCol += (bbg) * vec3(7.228506, 1.841278, -4.434168);
    outCol += (rgb_p) * vec3(-5.950417, -4.591002, 1.678724);
    outCol += (rr*rr) * vec3(-0.302577, 0.433225, 0.953560);
    outCol += (gg*gg) * vec3(3.231514, 1.893065, -1.536324);
    outCol += (bb*bb) * vec3(-4.909205, -4.300931, -0.432320);
    outCol += (rrr*g) * vec3(-1.016509, -0.756345, 0.826969);
    outCol += (rrr*b) * vec3(-1.665456, -1.387284, -0.776082);
    outCol += (ggg*r) * vec3(-0.442963, 0.053045, 2.067779);
    outCol += (ggg*b) * vec3(-4.182277, -0.675710, 0.430963);
    outCol += (bbb*r) * vec3(0.029660, 1.627451, -0.513682);
    outCol += (bbb*g) * vec3(-4.141914, -1.235174, 0.779007);
    outCol += (rr*gg) * vec3(1.403440, -1.000279, -2.479058);
    outCol += (rr*bb) * vec3(-4.102438, -1.111197, 0.666593);
    outCol += (gg*bb) * vec3(0.115577, -1.208541, -0.294794);
    outCol += (rr*gb) * vec3(-0.931934, 0.175821, -1.851695);
    outCol += (gg*rb) * vec3(1.990248, 1.434591, -0.346634);
    outCol += (bb*rg) * vec3(2.859718, 2.387324, 2.275881);
    outCol += (mx) * vec3(0.029031, -0.146013, -0.340185);
    outCol += (mn) * vec3(0.737413, 0.307309, 0.004390);
    outCol += (md) * vec3(-0.082821, 0.212562, 0.184535);
    outCol += (ch) * vec3(0.008470, -0.013964, 0.240506);
    outCol += (ch*r) * vec3(-2.802490, -0.606781, 1.581634);
    outCol += (ch*g) * vec3(-0.620486, 0.365157, 0.543929);
    outCol += (ch*b) * vec3(0.350024, -0.836404, -0.446058);
    outCol += (ch*mx) * vec3(1.375089, 0.399550, -0.473830);
    outCol += (ch*mn) * vec3(1.405478, 0.557835, -0.016386);
    outCol += (mx*mx) * vec3(-0.278165, 0.238704, 0.009010);
    outCol += (mn*mn) * vec3(-2.173420, -0.798200, 1.128359);
    outCol += (ch*ch) * vec3(-0.166264, -0.204177, -0.130360);
    outCol += msEvalTetra9(x);
    return clamp(outCol, 0.0, 1.0);
}

vec3 msGradePoint(vec3 rawRgb) {
    vec3 c = clamp(rawRgb, 0.0, 1.0);
    if (uColourCorrection > 0.5) {
        c = msApplyColour(c);
    }
    return c;
}
vec3 msFetchGraded(vec2 uv) {
    vec4 s = texture2D(uTexture, clamp(uv, 0.0, 1.0));
    vec3 rgb = s.rgb / max(s.a, 0.0001);
    return msGradePoint(rgb);
}

void main() {
    vec4 baseSample = texture2D(uTexture, clamp(vTex, 0.0, 1.0));
    float alpha = baseSample.a;
    vec3 rawCenter = baseSample.rgb / max(alpha, 0.0001);
    vec3 gradedCenter = msGradePoint(rawCenter);
    vec3 col = gradedCenter;
    if (uQuality > 0.5) { col = clamp(col, 0.0, 1.0); }
    col = clamp(col, 0.0, 1.0);
    gl_FragColor = vec4(col * alpha, alpha);
}
