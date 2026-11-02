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
                        return mix(0.094636, 0.091782, s - 0.0);
                    } else {
                        return mix(0.091782, 0.105980, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.105980, 0.131526, s - 2.0);
                    } else {
                        return mix(0.131526, 0.160221, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.160221, 0.187635, s - 4.0);
                    } else {
                        return mix(0.187635, 0.211440, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.211440, 0.230609, s - 6.0);
                    } else {
                        return mix(0.230609, 0.244216, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.244216, 0.258764, s - 8.0);
                    } else {
                        return mix(0.258764, 0.284918, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.284918, 0.324390, s - 10.0);
                    } else {
                        return mix(0.324390, 0.368707, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.368707, 0.411453, s - 12.0);
                    } else {
                        return mix(0.411453, 0.449073, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.449073, 0.477846, s - 14.0);
                    } else {
                        return mix(0.477846, 0.483480, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.483480, 0.472808, s - 16.0);
                    } else {
                        return mix(0.472808, 0.482759, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.482759, 0.512993, s - 18.0);
                    } else {
                        return mix(0.512993, 0.555467, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.555467, 0.600706, s - 20.0);
                    } else {
                        return mix(0.600706, 0.640663, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.640663, 0.674513, s - 22.0);
                    } else {
                        return mix(0.674513, 0.705933, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.705933, 0.742725, s - 24.0);
                    } else {
                        return mix(0.742725, 0.787828, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.787828, 0.835480, s - 26.0);
                    } else {
                        return mix(0.835480, 0.878475, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.878475, 0.921378, s - 28.0);
                    } else {
                        return mix(0.921378, 0.961350, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.961350, 0.989616, s - 30.0);
                    } else {
                        return mix(0.989616, 1.000000, s - 31.0);
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
                        return mix(0.122076, 0.133418, s - 0.0);
                    } else {
                        return mix(0.133418, 0.144592, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.144592, 0.156911, s - 2.0);
                    } else {
                        return mix(0.156911, 0.170039, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.170039, 0.185242, s - 4.0);
                    } else {
                        return mix(0.185242, 0.204516, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.204516, 0.233534, s - 6.0);
                    } else {
                        return mix(0.233534, 0.264870, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.264870, 0.296125, s - 8.0);
                    } else {
                        return mix(0.296125, 0.332577, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.332577, 0.375039, s - 10.0);
                    } else {
                        return mix(0.375039, 0.419993, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.419993, 0.463759, s - 12.0);
                    } else {
                        return mix(0.463759, 0.504303, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.504303, 0.537382, s - 14.0);
                    } else {
                        return mix(0.537382, 0.549048, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.549048, 0.544170, s - 16.0);
                    } else {
                        return mix(0.544170, 0.558702, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.558702, 0.590442, s - 18.0);
                    } else {
                        return mix(0.590442, 0.632588, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.632588, 0.677317, s - 20.0);
                    } else {
                        return mix(0.677317, 0.716991, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.716991, 0.745297, s - 22.0);
                    } else {
                        return mix(0.745297, 0.765663, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.765663, 0.786244, s - 24.0);
                    } else {
                        return mix(0.786244, 0.809670, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.809670, 0.831466, s - 26.0);
                    } else {
                        return mix(0.831466, 0.854858, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.854858, 0.894492, s - 28.0);
                    } else {
                        return mix(0.894492, 0.926677, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.926677, 0.948239, s - 30.0);
                    } else {
                        return mix(0.948239, 0.952919, s - 31.0);
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
                        return mix(0.137718, 0.152318, s - 0.0);
                    } else {
                        return mix(0.152318, 0.166679, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.166679, 0.180991, s - 2.0);
                    } else {
                        return mix(0.180991, 0.193677, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.193677, 0.207226, s - 4.0);
                    } else {
                        return mix(0.207226, 0.226046, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.226046, 0.261032, s - 6.0);
                    } else {
                        return mix(0.261032, 0.304993, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.304993, 0.350483, s - 8.0);
                    } else {
                        return mix(0.350483, 0.393424, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.393424, 0.434491, s - 10.0);
                    } else {
                        return mix(0.434491, 0.474393, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.474393, 0.513677, s - 12.0);
                    } else {
                        return mix(0.513677, 0.552431, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.552431, 0.587585, s - 14.0);
                    } else {
                        return mix(0.587585, 0.608525, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.608525, 0.616186, s - 16.0);
                    } else {
                        return mix(0.616186, 0.636925, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.636925, 0.670282, s - 18.0);
                    } else {
                        return mix(0.670282, 0.713206, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.713206, 0.759183, s - 20.0);
                    } else {
                        return mix(0.759183, 0.799455, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.799455, 0.818218, s - 22.0);
                    } else {
                        return mix(0.818218, 0.820204, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.820204, 0.817976, s - 24.0);
                    } else {
                        return mix(0.817976, 0.816975, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.816975, 0.815058, s - 26.0);
                    } else {
                        return mix(0.815058, 0.826989, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.826989, 0.867641, s - 28.0);
                    } else {
                        return mix(0.867641, 0.885828, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.885828, 0.889465, s - 30.0);
                    } else {
                        return mix(0.889465, 0.864161, s - 31.0);
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
                            return vec3(0.04727, 0.01178, -0.01101);
                          } else {
                            return vec3(0.01393, 0.00901, 0.00133);
                          }
                        } else {
                          return vec3(-0.00548, -0.01807, -0.01890);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.02161, -0.05444, -0.07061);
                        } else {
                          return vec3(-0.02091, -0.06302, -0.07293);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(0.00000, -0.04671, -0.01607);
                        } else {
                          return vec3(0.00000, -0.02189, 0.00000);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.00000, 0.00801, 0.00000);
                        } else {
                          return vec3(0.00000, 0.02103, 0.02020);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(-0.03670, -0.01928, -0.00209);
                          } else {
                            return vec3(0.00000, 0.01778, 0.03322);
                          }
                        } else {
                          return vec3(-0.00291, -0.00270, 0.01959);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.02870, -0.03718, -0.03239);
                        } else {
                          return vec3(-0.03757, -0.04332, -0.03046);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.02276, -0.03262, 0.02278);
                        } else {
                          return vec3(0.00000, -0.02024, 0.00000);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.00000, 0.00129, 0.00000);
                        } else {
                          return vec3(0.00000, 0.00883, 0.01047);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.05004, -0.03697, -0.00202);
                        } else {
                          return vec3(-0.00228, 0.00589, 0.03928);
                        }
                      } else {
                        return vec3(0.00000, 0.01945, 0.04192);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01491, -0.01587, -0.01107);
                      } else {
                        return vec3(-0.03374, -0.02284, -0.00506);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02971, -0.01590, 0.03984);
                      } else {
                        return vec3(-0.00849, -0.01525, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.00595, 0.00000);
                      } else {
                        return vec3(0.00000, -0.00716, 0.00000);
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
                          return vec3(-0.02738, -0.04294, -0.01210);
                        } else {
                          return vec3(0.00000, -0.00619, 0.03154);
                        }
                      } else {
                        return vec3(0.00000, 0.00417, 0.03063);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.00068, -0.00250);
                      } else {
                        return vec3(-0.00532, -0.01349, -0.00229);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.01240, -0.01400, 0.01516);
                      } else {
                        return vec3(-0.00587, -0.01711, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00112, -0.01633, 0.00000);
                      } else {
                        return vec3(-0.00173, -0.03001, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.00503, -0.03056, -0.02187);
                        } else {
                          return vec3(0.00000, 0.00038, 0.02731);
                        }
                      } else {
                        return vec3(0.00000, 0.00051, 0.02382);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.00963, -0.01752);
                      } else {
                        return vec3(0.00000, 0.00155, -0.00442);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.00103, 0.00976);
                      } else {
                        return vec3(0.00000, -0.00764, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.00721, 0.00000);
                      } else {
                        return vec3(-0.00565, -0.03046, 0.00000);
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
                          return vec3(0.00000, -0.00517, -0.02341);
                        } else {
                          return vec3(0.00000, 0.02053, 0.02949);
                        }
                      } else {
                        return vec3(0.00000, 0.01301, 0.02475);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.00831, -0.02829);
                      } else {
                        return vec3(0.00000, 0.00212, -0.02429);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.02108, 0.02424);
                      } else {
                        return vec3(0.00000, 0.01560, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.01592, 0.00000);
                      } else {
                        return vec3(-0.00313, -0.00826, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, -0.00771, -0.02772);
                        } else {
                          return vec3(0.00000, 0.01288, 0.03007);
                        }
                      } else {
                        return vec3(0.00000, -0.00064, 0.02676);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.03002, -0.03217);
                      } else {
                        return vec3(0.00000, -0.02847, -0.03975);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.00397, 0.02132);
                      } else {
                        return vec3(0.00000, 0.01588, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.02101, 0.00000);
                      } else {
                        return vec3(0.00000, 0.00237, 0.00986);
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
                          return vec3(0.00000, 0.00269, -0.03313);
                        } else {
                          return vec3(0.00000, 0.02127, 0.03044);
                        }
                      } else {
                        return vec3(0.00000, 0.00573, 0.03085);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.02648, -0.02872);
                      } else {
                        return vec3(-0.00065, -0.02923, -0.04126);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.00847, 0.01399);
                      } else {
                        return vec3(0.00000, 0.01867, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.04097, 0.00708);
                      } else {
                        return vec3(0.00000, 0.00000, 0.05472);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, 0.01383, -0.05196);
                        } else {
                          return vec3(0.00000, 0.03365, 0.02032);
                        }
                      } else {
                        return vec3(0.00000, 0.02011, 0.02775);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.01004, -0.02914);
                      } else {
                        return vec3(0.00000, -0.01257, -0.04433);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.00088, 0.00593);
                      } else {
                        return vec3(0.00000, 0.00000, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.00000, 0.00000);
                      } else {
                        return vec3(0.00000, 0.00000, 0.06937);
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
                            return vec3(-0.04855, 0.01285, -0.00575);
                          } else {
                            return vec3(0.01408, 0.02911, 0.02436);
                          }
                        } else {
                          return vec3(0.00952, 0.00344, 0.01517);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.02279, -0.03568, -0.04025);
                        } else {
                          return vec3(-0.04439, -0.04651, -0.05107);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.03933, -0.03007, -0.00620);
                        } else {
                          return vec3(-0.01396, -0.00769, 0.02251);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.01196, 0.01608, 0.00171);
                        } else {
                          return vec3(-0.00228, 0.02102, 0.01773);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(-0.03060, -0.00367, 0.00226);
                          } else {
                            return vec3(0.02931, 0.01521, 0.00518);
                          }
                        } else {
                          return vec3(0.01551, -0.00701, -0.00459);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.01058, -0.02578, -0.02870);
                        } else {
                          return vec3(-0.02247, -0.02683, -0.03070);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.02866, -0.01650, 0.00352);
                        } else {
                          return vec3(-0.02571, -0.00276, 0.02153);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.03091, 0.01923, 0.00050);
                        } else {
                          return vec3(-0.00526, 0.02716, 0.01749);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.03804, -0.02323, -0.00159);
                        } else {
                          return vec3(0.00422, 0.00088, 0.00735);
                        }
                      } else {
                        return vec3(0.00607, 0.00217, 0.00234);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02101, -0.01646, -0.01499);
                      } else {
                        return vec3(0.00044, -0.00503, -0.00750);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.03531, -0.00923, 0.00342);
                      } else {
                        return vec3(-0.06960, -0.01699, 0.00441);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.05085, 0.00789, 0.00000);
                      } else {
                        return vec3(-0.03341, 0.01353, 0.00000);
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
                          return vec3(-0.02943, -0.03352, -0.01763);
                        } else {
                          return vec3(-0.00294, -0.00439, 0.01352);
                        }
                      } else {
                        return vec3(-0.00903, -0.00015, 0.02312);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00674, -0.00573, -0.00741);
                      } else {
                        return vec3(-0.00505, 0.00365, -0.00710);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02885, 0.02446, 0.04661);
                      } else {
                        return vec3(-0.05866, -0.01879, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.04843, -0.00395, 0.00000);
                      } else {
                        return vec3(-0.04364, -0.01123, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.02011, -0.02635, -0.02974);
                        } else {
                          return vec3(-0.00074, 0.00402, 0.01335);
                        }
                      } else {
                        return vec3(-0.00965, 0.00497, 0.02662);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01667, -0.00639, -0.01267);
                      } else {
                        return vec3(-0.00443, 0.00918, -0.00862);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00086, 0.02537, 0.02398);
                      } else {
                        return vec3(-0.01055, 0.01793, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.03538, 0.00466, 0.00000);
                      } else {
                        return vec3(-0.04116, -0.01621, 0.00000);
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
                          return vec3(-0.01603, -0.00553, -0.03119);
                        } else {
                          return vec3(-0.00033, 0.02316, 0.01469);
                        }
                      } else {
                        return vec3(-0.01134, 0.01961, 0.02847);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02947, -0.00108, -0.01732);
                      } else {
                        return vec3(-0.02325, 0.00648, -0.02261);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00720, 0.02594, 0.01525);
                      } else {
                        return vec3(-0.02053, 0.02445, 0.00000);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.02232, 0.02530, 0.00000);
                      } else {
                        return vec3(-0.03616, 0.00516, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.01276, -0.01295, -0.03257);
                        } else {
                          return vec3(-0.00315, 0.01262, 0.01625);
                        }
                      } else {
                        return vec3(-0.01645, 0.00390, 0.03256);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.04199, -0.02331, -0.01643);
                      } else {
                        return vec3(-0.04980, -0.02449, -0.03071);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.03239, -0.00468, 0.01137);
                      } else {
                        return vec3(0.00000, 0.01373, 0.01405);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00502, 0.02407, 0.00000);
                      } else {
                        return vec3(-0.02808, 0.01078, 0.01110);
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
                          return vec3(-0.01560, -0.00783, -0.03608);
                        } else {
                          return vec3(-0.00988, 0.01687, 0.01685);
                        }
                      } else {
                        return vec3(-0.02266, 0.00662, 0.03737);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.05083, -0.02164, -0.01112);
                      } else {
                        return vec3(-0.06536, -0.02427, -0.02835);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.04785, -0.00556, 0.01036);
                      } else {
                        return vec3(-0.01310, 0.01838, 0.01971);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.04501, 0.01957);
                      } else {
                        return vec3(-0.01772, 0.01247, 0.04240);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.01745, -0.00337, -0.05392);
                        } else {
                          return vec3(-0.01362, 0.02383, 0.00601);
                        }
                      } else {
                        return vec3(-0.02322, 0.01620, 0.03364);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.05081, -0.00799, -0.01158);
                      } else {
                        return vec3(-0.06755, -0.00726, -0.03010);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.05199, 0.01374, 0.00496);
                      } else {
                        return vec3(-0.02982, 0.00585, 0.00714);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.02058, 0.00000, 0.00107);
                      } else {
                        return vec3(-0.02108, 0.00000, 0.04458);
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
                          return vec3(-0.04151, 0.00467, -0.00033);
                        } else {
                          return vec3(0.01167, 0.02678, 0.03983);
                        }
                      } else {
                        return vec3(0.03161, 0.02077, 0.04218);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00104, -0.02091, -0.01589);
                      } else {
                        return vec3(-0.02422, -0.03492, -0.03888);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.01962, -0.02105, -0.01134);
                      } else {
                        return vec3(0.00707, -0.00169, 0.05109);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01018, 0.01767, 0.01192);
                      } else {
                        return vec3(0.01292, 0.01531, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.03386, -0.01240, -0.00176);
                        } else {
                          return vec3(0.01526, 0.00849, 0.01673);
                        }
                      } else {
                        return vec3(0.01936, 0.01095, 0.02285);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00609, -0.01459, -0.00920);
                      } else {
                        return vec3(-0.01175, -0.01795, -0.02399);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00677, -0.00760, -0.00625);
                      } else {
                        return vec3(0.00370, 0.00138, 0.04926);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00209, 0.01717, 0.01511);
                      } else {
                        return vec3(-0.00340, 0.01718, 0.00456);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01809, -0.01232, -0.01137);
                      } else {
                        return vec3(0.01063, 0.00905, 0.00674);
                      }
                    } else {
                      return vec3(0.02267, 0.01121, 0.00723);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00701, -0.00947, -0.00678);
                    } else {
                      return vec3(0.01947, 0.00662, -0.01313);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02303, 0.00070, -0.02308);
                    } else {
                      return vec3(0.01683, 0.00055, 0.03177);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00785, 0.02204, 0.01215);
                    } else {
                      return vec3(0.00413, 0.02564, 0.00482);
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
                        return vec3(-0.00809, -0.02518, -0.00653);
                      } else {
                        return vec3(0.00738, -0.00067, 0.00734);
                      }
                    } else {
                      return vec3(0.01003, 0.00143, 0.01760);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00630, -0.00450, -0.00719);
                    } else {
                      return vec3(0.02019, 0.00820, -0.01377);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03029, -0.00412, -0.03389);
                    } else {
                      return vec3(0.02078, -0.01035, 0.01616);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00196, 0.00347, 0.00000);
                    } else {
                      return vec3(-0.01130, 0.00313, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00132, -0.02216, -0.01187);
                      } else {
                        return vec3(0.01359, 0.00512, 0.00569);
                      }
                    } else {
                      return vec3(0.02212, 0.01162, 0.02123);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01955, 0.00189, -0.01088);
                    } else {
                      return vec3(0.02612, 0.00809, -0.02128);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02783, 0.01781, -0.00369);
                    } else {
                      return vec3(0.02804, 0.01086, 0.01362);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00098, 0.00561, 0.00000);
                    } else {
                      return vec3(-0.00869, 0.00059, 0.00000);
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
                        return vec3(0.00113, -0.00500, -0.01767);
                      } else {
                        return vec3(0.01732, 0.02230, 0.00712);
                      }
                    } else {
                      return vec3(0.02298, 0.02618, 0.02258);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01132, 0.00564, -0.01426);
                    } else {
                      return vec3(0.00938, 0.00388, -0.03070);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01492, 0.01385, -0.01113);
                    } else {
                      return vec3(0.01065, 0.01411, 0.01809);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00602, 0.02576, 0.00000);
                    } else {
                      return vec3(-0.00169, 0.01991, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00548, -0.01594, -0.02344);
                      } else {
                        return vec3(0.01681, 0.00860, 0.01146);
                      }
                    } else {
                      return vec3(0.01472, 0.00847, 0.02771);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00075, -0.01792, -0.01026);
                    } else {
                      return vec3(-0.00820, -0.02392, -0.03119);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00304, -0.00987, -0.00883);
                    } else {
                      return vec3(0.02757, 0.00756, 0.03776);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01976, 0.02352, 0.00241);
                    } else {
                      return vec3(-0.00192, 0.01413, 0.00000);
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
                        return vec3(0.00308, -0.01482, -0.03143);
                      } else {
                        return vec3(0.01026, 0.00878, 0.01371);
                      }
                    } else {
                      return vec3(0.00451, 0.00885, 0.03258);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00793, -0.01635, -0.00350);
                    } else {
                      return vec3(-0.01275, -0.01932, -0.02485);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00273, -0.00288, -0.00323);
                    } else {
                      return vec3(0.01955, 0.01625, 0.04166);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02292, 0.03781, 0.01734);
                    } else {
                      return vec3(-0.01015, 0.02583, 0.01390);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00096, -0.01567, -0.05364);
                      } else {
                        return vec3(0.00613, 0.01072, 0.00352);
                      }
                    } else {
                      return vec3(-0.00008, 0.01579, 0.02780);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00576, -0.00311, -0.00433);
                    } else {
                      return vec3(-0.00688, -0.00032, -0.02615);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00055, 0.01842, -0.00741);
                    } else {
                      return vec3(0.00639, 0.02449, 0.02742);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00764, 0.00136, 0.00000);
                    } else {
                      return vec3(-0.03273, 0.00000, 0.00231);
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
                          return vec3(-0.01826, -0.00389, -0.00794);
                        } else {
                          return vec3(0.00910, 0.02525, 0.05016);
                        }
                      } else {
                        return vec3(0.00599, 0.01732, 0.05485);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00809, -0.01153, 0.00983);
                      } else {
                        return vec3(-0.02991, -0.02774, -0.02622);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02464, -0.01681, -0.01984);
                      } else {
                        return vec3(0.00136, 0.00025, 0.01646);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00379, 0.01763, 0.01892);
                      } else {
                        return vec3(0.00169, 0.00944, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.03330, -0.01412, -0.01120);
                        } else {
                          return vec3(-0.00403, 0.01004, 0.03529);
                        }
                      } else {
                        return vec3(-0.01129, 0.01300, 0.05313);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01826, -0.00252, 0.01890);
                      } else {
                        return vec3(-0.02248, -0.00579, -0.00645);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00985, 0.00533, -0.00469);
                      } else {
                        return vec3(0.00592, 0.01102, 0.02094);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00468, 0.01720, 0.02457);
                      } else {
                        return vec3(-0.01676, 0.00410, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.03276, -0.01758, -0.00845);
                      } else {
                        return vec3(-0.01815, 0.00619, 0.01693);
                      }
                    } else {
                      return vec3(-0.00754, 0.01138, 0.03566);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00672, 0.00995, 0.01789);
                    } else {
                      return vec3(0.01051, 0.02598, 0.01063);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02772, 0.03925, 0.01063);
                    } else {
                      return vec3(0.02141, 0.01800, 0.01256);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00241, 0.01494, 0.02419);
                    } else {
                      return vec3(-0.00440, 0.00904, 0.00000);
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
                        return vec3(-0.01847, -0.01965, 0.00000);
                      } else {
                        return vec3(-0.00798, 0.00485, -0.00265);
                      }
                    } else {
                      return vec3(0.00300, 0.01136, 0.01739);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04152, 0.02524, 0.01118);
                    } else {
                      return vec3(0.05659, 0.04446, 0.02079);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03457, 0.03774, 0.01329);
                    } else {
                      return vec3(0.01227, -0.00265, -0.00677);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01587, 0.00489, 0.02774);
                    } else {
                      return vec3(0.04627, 0.02710, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01362, -0.01807, 0.00000);
                      } else {
                        return vec3(-0.00047, 0.00750, -0.00980);
                      }
                    } else {
                      return vec3(0.01164, 0.01454, 0.01746);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04063, 0.02186, 0.00410);
                    } else {
                      return vec3(0.03521, 0.01765, -0.01275);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03520, -0.02466, -0.03139);
                    } else {
                      return vec3(-0.04650, -0.03627, -0.02303);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00898, 0.00232, 0.01177);
                    } else {
                      return vec3(0.06260, 0.03192, 0.00000);
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
                        return vec3(-0.01127, -0.00217, 0.00000);
                      } else {
                        return vec3(0.00438, 0.02272, -0.00831);
                      }
                    } else {
                      return vec3(0.01212, 0.02567, 0.02001);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02106, 0.01653, -0.00258);
                    } else {
                      return vec3(0.00274, -0.00145, -0.03140);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02588, -0.01550, -0.03438);
                    } else {
                      return vec3(-0.01350, -0.00303, -0.00160);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03782, 0.03841, 0.00814);
                    } else {
                      return vec3(0.05397, 0.03897, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00541, -0.01414, 0.00000);
                      } else {
                        return vec3(0.00681, 0.00763, -0.00028);
                      }
                    } else {
                      return vec3(0.00502, 0.00558, 0.02868);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00351, -0.00908, 0.00253);
                    } else {
                      return vec3(-0.00307, -0.01957, -0.02254);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00918, -0.00886, -0.01871);
                    } else {
                      return vec3(0.04358, 0.00870, 0.01587);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04565, 0.02633, 0.01185);
                    } else {
                      return vec3(0.02790, 0.01280, 0.00000);
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
                        return vec3(-0.00688, -0.01477, 0.00000);
                      } else {
                        return vec3(0.00232, 0.00586, 0.00428);
                      }
                    } else {
                      return vec3(-0.00320, 0.00455, 0.03585);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00236, -0.00498, 0.01082);
                    } else {
                      return vec3(0.00416, -0.00764, -0.01293);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02003, 0.00582, -0.00933);
                    } else {
                      return vec3(0.04092, 0.01569, 0.02331);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03622, 0.02698, 0.01147);
                    } else {
                      return vec3(-0.00001, 0.00615, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00817, -0.01829, -0.01326);
                      } else {
                        return vec3(0.00056, 0.00533, -0.00474);
                      }
                    } else {
                      return vec3(-0.00426, 0.01055, 0.03237);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00211, 0.01050, 0.00925);
                    } else {
                      return vec3(0.01655, 0.01322, -0.01663);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02804, 0.02563, -0.01768);
                    } else {
                      return vec3(0.03078, 0.02867, 0.00920);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00564, 0.01583, 0.00000);
                    } else {
                      return vec3(-0.03127, 0.00000, 0.00000);
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
                          return vec3(0.00894, -0.00352, -0.03074);
                        } else {
                          return vec3(0.01496, 0.02331, 0.03744);
                        }
                      } else {
                        return vec3(-0.00795, 0.01224, 0.05069);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02589, -0.01559, 0.01530);
                      } else {
                        return vec3(-0.02919, -0.02477, -0.01334);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02308, -0.01432, -0.02418);
                      } else {
                        return vec3(-0.00052, 0.00019, -0.01440);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00210, 0.01508, 0.03417);
                      } else {
                        return vec3(-0.01201, 0.00229, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.01079, -0.00902, -0.03276);
                        } else {
                          return vec3(0.00559, 0.01101, 0.02908);
                        }
                      } else {
                        return vec3(-0.01801, 0.01055, 0.05506);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02960, -0.00420, 0.02730);
                      } else {
                        return vec3(-0.02228, -0.00177, 0.00557);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.01182, 0.01021, -0.00400);
                      } else {
                        return vec3(0.00268, 0.01430, -0.00321);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.01061, 0.01553, 0.03978);
                      } else {
                        return vec3(-0.02927, -0.00510, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.02496, -0.01505, 0.00000);
                      } else {
                        return vec3(-0.01512, 0.00802, 0.00729);
                      }
                    } else {
                      return vec3(-0.01310, 0.01022, 0.03884);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00897, 0.01079, 0.02476);
                    } else {
                      return vec3(0.01089, 0.02986, 0.01800);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02226, 0.04420, 0.01348);
                    } else {
                      return vec3(0.01051, 0.01976, -0.00768);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00963, 0.00920, 0.03740);
                    } else {
                      return vec3(-0.01527, -0.00220, 0.00000);
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
                        return vec3(-0.02485, -0.02165, 0.00000);
                      } else {
                        return vec3(-0.01522, 0.00302, -0.02120);
                      }
                    } else {
                      return vec3(-0.00537, 0.00849, 0.01528);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03509, 0.02288, 0.01687);
                    } else {
                      return vec3(0.06509, 0.05741, 0.03214);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03675, 0.03946, 0.01270);
                    } else {
                      return vec3(-0.01503, -0.02146, -0.03798);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00069, -0.00566, 0.04356);
                    } else {
                      return vec3(0.04886, 0.02280, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.02499, -0.01852, 0.00000);
                      } else {
                        return vec3(-0.01101, 0.00604, -0.03987);
                      }
                    } else {
                      return vec3(-0.00138, 0.01023, -0.00128);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03390, 0.02095, -0.00048);
                    } else {
                      return vec3(0.05643, 0.03925, 0.01571);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.06072, -0.04821, -0.03388);
                    } else {
                      return vec3(-0.07663, -0.06769, -0.05989);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04564, 0.02872, 0.05852);
                    } else {
                      return vec3(0.09735, 0.05560, 0.00515);
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
                        return vec3(-0.02264, -0.00155, 0.00000);
                      } else {
                        return vec3(-0.00789, 0.02055, -0.03926);
                      }
                    } else {
                      return vec3(-0.00401, 0.01894, 0.00294);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00728, 0.01157, -0.00507);
                    } else {
                      return vec3(-0.00082, 0.00180, -0.01715);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03288, -0.01465, -0.02720);
                    } else {
                      return vec3(0.01099, 0.01708, -0.00810);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08664, 0.06612, 0.04548);
                    } else {
                      return vec3(0.06492, 0.04769, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01586, -0.01205, 0.00000);
                      } else {
                        return vec3(-0.00386, 0.00678, -0.02877);
                      }
                    } else {
                      return vec3(-0.00794, -0.00015, 0.01634);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00901, -0.01266, 0.00430);
                    } else {
                      return vec3(-0.00184, -0.00841, -0.00289);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01174, 0.00196, -0.00897);
                    } else {
                      return vec3(0.04035, 0.01288, -0.00334);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03539, 0.02324, 0.03307);
                    } else {
                      return vec3(0.01209, 0.00129, 0.00000);
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
                        return vec3(-0.01627, -0.01174, 0.00000);
                      } else {
                        return vec3(-0.00575, 0.00649, -0.02217);
                      }
                    } else {
                      return vec3(-0.01140, 0.00074, 0.02721);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01044, -0.00532, 0.01548);
                    } else {
                      return vec3(0.00835, 0.00704, 0.00530);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02432, 0.01565, -0.00547);
                    } else {
                      return vec3(0.03046, 0.01114, -0.00576);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00830, 0.00815, 0.01767);
                    } else {
                      return vec3(-0.03118, -0.02102, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01555, -0.01424, 0.00000);
                      } else {
                        return vec3(-0.00365, 0.00764, -0.02995);
                      }
                    } else {
                      return vec3(-0.00605, 0.00898, 0.02626);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00089, 0.01274, 0.01438);
                    } else {
                      return vec3(0.02109, 0.02817, -0.00420);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03281, 0.03083, -0.02615);
                    } else {
                      return vec3(0.02821, 0.01929, -0.03445);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00761, 0.01216, 0.00000);
                    } else {
                      return vec3(-0.05678, 0.00000, 0.00000);
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
                          return vec3(0.04118, -0.01810, -0.10062);
                        } else {
                          return vec3(0.03997, 0.01121, -0.01393);
                        }
                      } else {
                        return vec3(0.01491, 0.00507, 0.02203);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01032, -0.02013, -0.00008);
                      } else {
                        return vec3(-0.00473, -0.02684, -0.01596);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00920, -0.01471, -0.02712);
                      } else {
                        return vec3(0.02474, -0.00328, -0.03901);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01757, 0.00837, 0.03824);
                      } else {
                        return vec3(0.00086, -0.00688, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.02523, -0.01610, -0.03400);
                        } else {
                          return vec3(0.04879, 0.00460, -0.01292);
                        }
                      } else {
                        return vec3(0.01067, 0.00511, 0.02963);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01188, -0.01176, 0.01203);
                      } else {
                        return vec3(-0.00272, -0.01231, -0.00445);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.01059, -0.00036, -0.01585);
                      } else {
                        return vec3(0.02031, 0.00455, -0.03117);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00834, 0.00932, 0.03983);
                      } else {
                        return vec3(-0.01046, -0.00901, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.01163, -0.01597, 0.00000);
                      } else {
                        return vec3(0.02103, 0.00614, -0.02905);
                      }
                    } else {
                      return vec3(0.01175, 0.00405, 0.01530);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00477, -0.00253, 0.00932);
                    } else {
                      return vec3(0.01623, 0.00223, -0.00660);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02320, 0.00913, -0.01976);
                    } else {
                      return vec3(0.02425, 0.00483, -0.03884);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01367, 0.00768, 0.02901);
                    } else {
                      return vec3(0.00514, -0.00433, 0.00000);
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
                        return vec3(0.00666, -0.02078, 0.00000);
                      } else {
                        return vec3(0.01450, 0.00188, -0.05065);
                      }
                    } else {
                      return vec3(0.01594, 0.00132, -0.00441);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03381, -0.00055, 0.00063);
                    } else {
                      return vec3(0.04298, 0.00489, -0.01358);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03597, 0.00079, -0.02778);
                    } else {
                      return vec3(0.03453, -0.00723, -0.04612);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04187, 0.00744, 0.02492);
                    } else {
                      return vec3(0.05539, 0.01006, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00045, -0.02026, 0.00000);
                      } else {
                        return vec3(0.01147, 0.00137, -0.04974);
                      }
                    } else {
                      return vec3(0.01367, -0.00091, -0.02493);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02887, -0.00554, -0.02133);
                    } else {
                      return vec3(0.04918, 0.00770, -0.00885);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04089, 0.00746, -0.00531);
                    } else {
                      return vec3(0.05973, 0.01625, -0.01027);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08607, 0.04152, 0.05381);
                    } else {
                      return vec3(0.09883, 0.04219, 0.00592);
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
                        return vec3(-0.00590, -0.00722, 0.00000);
                      } else {
                        return vec3(0.00707, 0.01182, -0.04446);
                      }
                    } else {
                      return vec3(0.00606, 0.00505, -0.03018);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01043, -0.00788, -0.03395);
                    } else {
                      return vec3(0.03006, 0.00878, -0.01334);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04618, 0.03250, 0.01891);
                    } else {
                      return vec3(0.07547, 0.05420, 0.03387);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.09353, 0.07108, 0.08297);
                    } else {
                      return vec3(0.08310, 0.05509, 0.02286);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00083, -0.01511, 0.00000);
                      } else {
                        return vec3(0.01206, 0.00141, -0.02831);
                      }
                    } else {
                      return vec3(0.00632, -0.00845, -0.01109);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00368, -0.02337, -0.01375);
                    } else {
                      return vec3(0.02326, -0.00252, 0.00393);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04599, 0.02103, 0.01643);
                    } else {
                      return vec3(0.05420, 0.02107, 0.00580);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01543, 0.01075, 0.06613);
                    } else {
                      return vec3(0.01295, -0.00474, 0.00000);
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
                        return vec3(0.00131, -0.01231, 0.00000);
                      } else {
                        return vec3(0.01298, 0.00494, -0.01922);
                      }
                    } else {
                      return vec3(0.00772, -0.00263, 0.00408);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00632, -0.01298, 0.00218);
                    } else {
                      return vec3(0.02696, 0.00997, 0.00917);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04599, 0.02360, 0.00153);
                    } else {
                      return vec3(0.03550, 0.00522, -0.02559);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.01866, -0.01707, 0.03410);
                    } else {
                      return vec3(-0.03562, -0.03837, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00471, -0.01133, 0.00000);
                      } else {
                        return vec3(0.01954, 0.01050, -0.02628);
                      }
                    } else {
                      return vec3(0.01842, 0.00988, 0.00573);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02009, 0.00688, 0.00272);
                    } else {
                      return vec3(0.03723, 0.02991, -0.00491);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.05039, 0.03421, -0.03146);
                    } else {
                      return vec3(0.04440, 0.01009, -0.07150);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00947, -0.00232, -0.00165);
                    } else {
                      return vec3(-0.04958, -0.01601, 0.00000);
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
                          return vec3(0.00000, -0.03687, -0.06898);
                        } else {
                          return vec3(0.01912, 0.00475, -0.07332);
                        }
                      } else {
                        return vec3(0.01921, 0.01075, 0.00191);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00961, -0.00878, 0.00538);
                      } else {
                        return vec3(-0.01864, -0.01645, -0.00892);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00269, -0.01133, -0.01206);
                      } else {
                        return vec3(0.01431, -0.00583, -0.02950);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00121, 0.00490, 0.02735);
                      } else {
                        return vec3(-0.02854, -0.01064, 0.00000);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, -0.02370, -0.00855);
                        } else {
                          return vec3(0.01864, -0.00301, -0.05407);
                        }
                      } else {
                        return vec3(0.00436, 0.00704, 0.00880);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02033, -0.00901, 0.01498);
                      } else {
                        return vec3(-0.02755, -0.01471, -0.00075);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.01406, -0.01022, -0.01001);
                      } else {
                        return vec3(0.00104, -0.00552, -0.02949);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.01289, 0.00563, 0.02907);
                      } else {
                        return vec3(-0.03791, -0.00832, 0.00000);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.01451, -0.01066, 0.00000);
                      } else {
                        return vec3(0.01302, 0.00818, -0.02412);
                      }
                    } else {
                      return vec3(-0.00605, 0.00113, -0.00413);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01959, -0.01104, 0.00926);
                    } else {
                      return vec3(-0.02404, -0.01540, -0.00657);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.01263, -0.01157, -0.02184);
                    } else {
                      return vec3(0.00318, -0.00604, -0.04157);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00647, 0.00723, 0.02006);
                    } else {
                      return vec3(-0.02765, -0.00478, 0.00000);
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
                        return vec3(0.01347, -0.00929, 0.00000);
                      } else {
                        return vec3(0.01365, 0.00832, -0.01320);
                      }
                    } else {
                      return vec3(-0.00232, -0.00193, -0.01643);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01137, -0.02047, -0.00053);
                    } else {
                      return vec3(-0.01011, -0.02225, -0.01194);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00444, -0.01429, -0.02763);
                    } else {
                      return vec3(0.02588, -0.00462, -0.04466);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02135, 0.01010, 0.01751);
                    } else {
                      return vec3(0.00309, -0.00310, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00369, -0.00776, 0.00000);
                      } else {
                        return vec3(0.00756, 0.00833, -0.01296);
                      }
                    } else {
                      return vec3(-0.00578, -0.00350, -0.03048);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01493, -0.02287, -0.01285);
                    } else {
                      return vec3(-0.00027, -0.01084, 0.00675);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02186, 0.00886, 0.00671);
                    } else {
                      return vec3(0.04775, 0.02364, -0.00441);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04548, 0.03434, 0.04359);
                    } else {
                      return vec3(0.02934, 0.01621, 0.00000);
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
                        return vec3(-0.01236, -0.00054, 0.00000);
                      } else {
                        return vec3(-0.00563, 0.01417, -0.01143);
                      }
                    } else {
                      return vec3(-0.01721, 0.00103, -0.03747);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02592, -0.01844, -0.02271);
                    } else {
                      return vec3(-0.00761, 0.00043, 0.00565);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02867, 0.04597, 0.06012);
                    } else {
                      return vec3(0.05179, 0.06926, 0.07159);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04704, 0.06554, 0.07853);
                    } else {
                      return vec3(0.03274, 0.04598, 0.02595);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.02699, -0.02103, 0.00000);
                      } else {
                        return vec3(-0.01688, -0.00617, -0.00393);
                      }
                    } else {
                      return vec3(-0.02540, -0.01819, -0.03069);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03276, -0.03563, -0.01932);
                    } else {
                      return vec3(-0.01836, -0.01771, -0.00298);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01397, 0.02466, 0.03914);
                    } else {
                      return vec3(0.03684, 0.04207, 0.04298);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01539, 0.04304, 0.08796);
                    } else {
                      return vec3(0.00784, 0.03129, 0.04936);
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
                        return vec3(-0.02409, -0.01065, 0.00000);
                      } else {
                        return vec3(-0.01117, 0.00623, 0.00000);
                      }
                    } else {
                      return vec3(-0.01712, -0.00282, -0.01063);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02432, -0.01770, 0.00431);
                    } else {
                      return vec3(-0.01479, -0.00292, 0.00991);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00573, 0.02387, 0.02078);
                    } else {
                      return vec3(0.01193, 0.01697, -0.01065);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02543, 0.00001, 0.02305);
                    } else {
                      return vec3(-0.04686, -0.01979, 0.00000);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01519, -0.00026, 0.00000);
                      } else {
                        return vec3(0.00270, 0.02164, 0.00000);
                      }
                    } else {
                      return vec3(0.00159, 0.01866, -0.00629);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00373, 0.00828, 0.00850);
                    } else {
                      return vec3(0.00163, 0.02081, -0.00019);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01273, 0.04138, -0.00445);
                    } else {
                      return vec3(0.01547, 0.02850, -0.04160);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.01665, 0.00399, -0.00862);
                    } else {
                      return vec3(-0.07507, -0.03297, 0.00000);
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
                          return vec3(0.00000, -0.00775, -0.03452);
                        } else {
                          return vec3(0.00000, 0.00000, -0.01737);
                        }
                      } else {
                        return vec3(0.00337, 0.02332, -0.01576);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00718, 0.01289, 0.01892);
                      } else {
                        return vec3(0.01576, 0.00727, 0.01199);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02446, 0.00891, -0.00296);
                      } else {
                        return vec3(0.02416, 0.00229, -0.02809);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01210, 0.00346, 0.03440);
                      } else {
                        return vec3(-0.02326, -0.01412, 0.04226);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, -0.03021, 0.00000);
                        } else {
                          return vec3(0.00000, -0.00600, -0.01013);
                        }
                      } else {
                        return vec3(0.00000, 0.01321, -0.01323);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.00338, 0.02424);
                      } else {
                        return vec3(0.00655, -0.00080, 0.01779);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00390, 0.00289, 0.00194);
                      } else {
                        return vec3(0.00475, -0.00100, -0.02485);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00638, 0.00269, 0.03672);
                      } else {
                        return vec3(-0.04010, -0.01257, 0.04219);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, -0.00809, 0.00000);
                      } else {
                        return vec3(0.00000, 0.00932, 0.00000);
                      }
                    } else {
                      return vec3(0.00000, 0.00088, -0.02841);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.00824, 0.01476);
                    } else {
                      return vec3(-0.00012, -0.01024, 0.01106);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00306, -0.00327, -0.00415);
                    } else {
                      return vec3(0.00055, -0.00402, -0.03258);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00993, 0.00139, 0.02642);
                    } else {
                      return vec3(-0.04310, -0.01361, 0.02817);
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
                        return vec3(0.00000, 0.00013, 0.00000);
                      } else {
                        return vec3(0.00859, 0.01433, 0.00000);
                      }
                    } else {
                      return vec3(0.00144, -0.00129, -0.03554);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.02513, 0.00392);
                    } else {
                      return vec3(-0.00195, -0.02299, 0.00688);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00418, -0.01068, -0.00476);
                    } else {
                      return vec3(0.01187, -0.00861, -0.03593);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00120, -0.00362, 0.01534);
                    } else {
                      return vec3(-0.03192, -0.02170, 0.01012);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00929, 0.00572, 0.00000);
                      } else {
                        return vec3(0.02551, 0.01839, 0.00000);
                      }
                    } else {
                      return vec3(0.01958, 0.00171, -0.04257);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00386, -0.02337, 0.00032);
                    } else {
                      return vec3(-0.00438, -0.01458, 0.02700);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01094, 0.00353, 0.02209);
                    } else {
                      return vec3(0.02220, 0.00783, -0.01313);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01252, 0.01101, 0.02264);
                    } else {
                      return vec3(-0.01648, -0.00986, 0.00780);
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
                        return vec3(0.01057, 0.01486, 0.00000);
                      } else {
                        return vec3(0.02991, 0.02761, 0.00000);
                      }
                    } else {
                      return vec3(0.01574, 0.01180, -0.04352);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01116, -0.01177, 0.00161);
                    } else {
                      return vec3(-0.01187, 0.00030, 0.03550);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00735, 0.02929, 0.05848);
                    } else {
                      return vec3(0.02184, 0.03275, 0.01168);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02113, 0.04165, 0.03412);
                    } else {
                      return vec3(0.00042, 0.02309, 0.01849);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, -0.00942, 0.00000);
                      } else {
                        return vec3(0.01807, 0.00529, 0.00000);
                      }
                    } else {
                      return vec3(0.00173, -0.00770, -0.03881);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02034, -0.02864, 0.00534);
                    } else {
                      return vec3(-0.02347, -0.01790, 0.02985);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00975, 0.00937, 0.04932);
                    } else {
                      return vec3(0.01552, 0.02124, 0.01947);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03284, 0.04182, 0.03266);
                    } else {
                      return vec3(0.00598, 0.02307, 0.04135);
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
                        return vec3(-0.00213, -0.02133, 0.00000);
                      } else {
                        return vec3(-0.00362, -0.00299, 0.00000);
                      }
                    } else {
                      return vec3(-0.01230, -0.01175, -0.03903);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02929, -0.02944, 0.00058);
                    } else {
                      return vec3(-0.03350, -0.01910, 0.01323);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02539, 0.00376, 0.01795);
                    } else {
                      return vec3(-0.00939, -0.00043, -0.02809);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.00316, 0.00200, 0.00214);
                    } else {
                      return vec3(-0.02711, 0.00017, 0.05671);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00468, 0.00046, -0.00522);
                      } else {
                        return vec3(0.01550, 0.02355, 0.00000);
                      }
                    } else {
                      return vec3(0.01292, 0.01972, -0.03563);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00136, 0.00504, 0.00614);
                    } else {
                      return vec3(-0.00817, 0.01471, 0.01257);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00662, 0.03818, 0.01916);
                    } else {
                      return vec3(-0.00471, 0.05256, 0.02157);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02500, 0.03791, 0.05287);
                    } else {
                      return vec3(-0.07676, -0.04390, -0.01738);
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
                          return vec3(0.00000, 0.00000, -0.02573);
                        } else {
                          return vec3(0.04808, 0.00000, 0.00000);
                        }
                      } else {
                        return vec3(0.06450, 0.00000, -0.00031);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.05255, 0.02345, 0.00541);
                      } else {
                        return vec3(0.04042, 0.02414, 0.01080);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.03595, 0.02767, -0.00762);
                      } else {
                        return vec3(0.03157, 0.02041, -0.04997);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.02311, 0.02128, -0.00282);
                      } else {
                        return vec3(0.00000, -0.00898, 0.02062);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, -0.05416, 0.00000);
                        } else {
                          return vec3(0.00569, -0.02399, 0.00000);
                        }
                      } else {
                        return vec3(0.02774, 0.00596, -0.00259);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.02217, 0.00671, 0.00582);
                      } else {
                        return vec3(0.01447, 0.00990, 0.01449);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.01254, 0.01802, 0.00012);
                      } else {
                        return vec3(0.00897, 0.01521, -0.03870);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00003, 0.01878, 0.01050);
                      } else {
                        return vec3(0.00000, -0.01022, 0.03536);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00538, -0.02570, 0.00000);
                      } else {
                        return vec3(0.00918, -0.00636, 0.00000);
                      }
                    } else {
                      return vec3(0.00000, -0.01173, -0.02257);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.01150, -0.00787);
                    } else {
                      return vec3(0.00000, -0.00538, 0.00592);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, 0.00732, -0.00348);
                    } else {
                      return vec3(0.00000, 0.00806, -0.03911);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.01334, 0.01094);
                    } else {
                      return vec3(0.00000, -0.01578, 0.03559);
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
                        return vec3(0.01800, -0.01118, 0.00000);
                      } else {
                        return vec3(0.02328, 0.00313, 0.00000);
                      }
                    } else {
                      return vec3(0.00045, -0.01178, -0.02895);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.03305, -0.02111);
                    } else {
                      return vec3(0.00000, -0.02446, -0.00181);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, -0.00887, -0.00865);
                    } else {
                      return vec3(0.00000, -0.00624, -0.04406);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.00066, 0.00489);
                    } else {
                      return vec3(0.00000, -0.02909, 0.02677);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.02077, 0.00015, -0.00075);
                      } else {
                        return vec3(0.02966, 0.01309, 0.00000);
                      }
                    } else {
                      return vec3(0.01044, -0.00263, -0.03310);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.02724, -0.01903);
                    } else {
                      return vec3(0.00000, -0.02130, 0.01324);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, -0.00731, -0.00094);
                    } else {
                      return vec3(0.00000, -0.00451, -0.04432);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.00745, 0.00291);
                    } else {
                      return vec3(0.00000, -0.01913, 0.02161);
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
                        return vec3(0.01460, 0.01361, -0.01224);
                      } else {
                        return vec3(0.02801, 0.02793, 0.00000);
                      }
                    } else {
                      return vec3(0.01353, 0.01406, -0.03202);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.00945, -0.00983);
                    } else {
                      return vec3(0.00000, -0.00432, 0.02539);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, 0.01142, 0.02126);
                    } else {
                      return vec3(0.00000, 0.00867, -0.04557);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.02517, -0.00731);
                    } else {
                      return vec3(0.00000, 0.00485, 0.00761);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, -0.00453, -0.02287);
                      } else {
                        return vec3(0.01931, 0.01265, 0.00000);
                      }
                    } else {
                      return vec3(0.01284, 0.00183, -0.02633);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.01970, 0.00083);
                    } else {
                      return vec3(0.00000, -0.01432, 0.03470);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, 0.00546, 0.04110);
                    } else {
                      return vec3(0.00000, 0.00815, -0.01165);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.00492, -0.01977);
                    } else {
                      return vec3(0.00000, -0.01982, -0.02276);
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
                        return vec3(0.00000, -0.00953, -0.03520);
                      } else {
                        return vec3(0.01151, 0.01121, -0.00322);
                      }
                    } else {
                      return vec3(0.01345, 0.00391, -0.02582);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00000, -0.01485, 0.00064);
                    } else {
                      return vec3(0.00000, -0.00583, 0.03700);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00000, 0.02304, 0.06186);
                    } else {
                      return vec3(0.00000, 0.04673, 0.05563);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.01815, 0.00635);
                    } else {
                      return vec3(0.00000, -0.05130, -0.06233);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00000, -0.01476, -0.06439);
                      } else {
                        return vec3(0.01113, 0.01099, -0.02413);
                      }
                    } else {
                      return vec3(0.02346, 0.00864, -0.04362);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01755, -0.00603, -0.02353);
                    } else {
                      return vec3(0.01453, 0.00839, 0.01226);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01614, 0.05109, 0.06019);
                    } else {
                      return vec3(0.01160, 0.07110, 0.07756);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00000, 0.03076, 0.03460);
                    } else {
                      return vec3(0.00000, -0.04708, -0.13584);
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
    vec3 outCol = vec3(0.034450, 0.115217, 0.157525);
    outCol += (r) * vec3(2.277188, 0.409650, 0.520310);
    outCol += (g) * vec3(0.085584, 1.182775, -0.756682);
    outCol += (b) * vec3(-1.484102, -0.795920, 1.545437);
    outCol += (rr) * vec3(-1.686666, 0.224861, 1.400002);
    outCol += (gg) * vec3(-1.562414, -1.719114, 4.096681);
    outCol += (bb) * vec3(3.901858, 4.285879, 0.996618);
    outCol += (rg) * vec3(-0.981277, 0.054798, -0.104309);
    outCol += (rb) * vec3(-0.059978, 0.378240, -1.775660);
    outCol += (gb) * vec3(1.713840, 2.235141, 2.858290);
    outCol += (rrr) * vec3(2.125294, -0.375015, -2.332971);
    outCol += (ggg) * vec3(2.187843, 2.722457, -4.361521);
    outCol += (bbb) * vec3(-6.085777, -5.843352, -0.918648);
    outCol += (rrg) * vec3(1.775494, 0.281392, 1.542099);
    outCol += (rrb) * vec3(0.396932, 0.252757, 0.887216);
    outCol += (ggr) * vec3(1.596364, 0.642194, -0.065530);
    outCol += (ggb) * vec3(-1.286824, -1.202368, -3.349591);
    outCol += (bbr) * vec3(-0.113787, -0.394827, 1.920207);
    outCol += (bbg) * vec3(-0.377800, -1.784153, -0.017222);
    outCol += (rgb_p) * vec3(-2.070953, -1.715812, -3.086942);
    outCol += (rr*rr) * vec3(-1.389506, 0.429950, 1.183957);
    outCol += (gg*gg) * vec3(-0.870991, -1.185554, 1.705411);
    outCol += (bb*bb) * vec3(2.551417, 2.652853, -0.750875);
    outCol += (rrr*g) * vec3(-0.113203, -0.011301, -0.157768);
    outCol += (rrr*b) * vec3(-0.286334, -0.545100, -0.579594);
    outCol += (ggg*r) * vec3(-0.360805, 0.013410, 0.333862);
    outCol += (ggg*b) * vec3(0.044510, -0.206427, 0.744165);
    outCol += (bbb*r) * vec3(0.456088, 0.492259, 1.174250);
    outCol += (bbb*g) * vec3(0.494669, 0.549903, -0.617580);
    outCol += (rr*gg) * vec3(-1.054244, -0.734976, -0.597807);
    outCol += (rr*bb) * vec3(0.577036, 0.109447, -0.498337);
    outCol += (gg*bb) * vec3(0.473629, 0.738253, 1.185361);
    outCol += (rr*gb) * vec3(0.212539, 0.432764, -0.350646);
    outCol += (gg*rb) * vec3(0.390709, 0.705238, 1.395945);
    outCol += (bb*rg) * vec3(0.039369, 0.580296, 0.952739);
    outCol += (mx) * vec3(0.156998, -0.152141, -0.670010);
    outCol += (mn) * vec3(-0.385536, -0.392686, -0.435681);
    outCol += (md) * vec3(-0.062282, -0.544335, -0.808115);
    outCol += (ch) * vec3(0.121989, 0.001559, -0.037810);
    outCol += (ch*r) * vec3(-0.973390, -0.512883, -0.920891);
    outCol += (ch*g) * vec3(-0.585945, 0.039500, -0.774935);
    outCol += (ch*b) * vec3(0.188706, 0.234331, -0.221850);
    outCol += (ch*mx) * vec3(0.114066, -0.041992, 0.410115);
    outCol += (ch*mn) * vec3(0.197462, -0.169549, 0.233468);
    outCol += (mx*mx) * vec3(0.257455, -0.144185, 0.186227);
    outCol += (mn*mn) * vec3(-0.423810, -0.578248, -1.408400);
    outCol += (ch*ch) * vec3(-0.004855, -0.005403, 0.193492);
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

// --- Plugin: gradient (multiply, uses yTop = 1.0 - uv.y, 0 extra taps) ---
vec3 msApplyGradient(vec3 col, vec2 uv) {
    float yTop = 1.0 - uv.y;
    float t = 0.5 + (uv.x - 0.5) * 0.181429 + (yTop - 0.5) * -0.983404;
    float u = clamp((t - (0.355400)) / 0.434400, 0.0, 1.0);
    float s = u * u * (3.0 - 2.0 * u);
    return clamp(col * (vec3(1.0) + s * vec3(0.043210, 0.049380, 0.045500)), 0.0, 1.0);
}

void main() {
    vec4 baseSample = texture2D(uTexture, clamp(vTex, 0.0, 1.0));
    float alpha = baseSample.a;
    vec3 rawCenter = baseSample.rgb / max(alpha, 0.0001);
    vec3 gradedCenter = msGradePoint(rawCenter);
    vec3 col = gradedCenter;
    if (uQuality > 0.5) { col = msApplyGradient(col, vTex); }
    col = clamp(col, 0.0, 1.0);
    gl_FragColor = vec4(col * alpha, alpha);
}
