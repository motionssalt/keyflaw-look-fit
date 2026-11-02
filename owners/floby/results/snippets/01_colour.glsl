// --- Plugin: colour (GLSL ES 1.00, 0 texture taps) ---
float msCurveR(float x) {
    float s = clamp(x, 0.0, 1.0) * 32.0;
    if (s < 16.0) {
        if (s < 8.0) {
            if (s < 4.0) {
                if (s < 2.0) {
                    if (s < 1.0) {
                        return mix(0.021804, 0.095821, s - 0.0);
                    } else {
                        return mix(0.095821, 0.148040, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.148040, 0.175059, s - 2.0);
                    } else {
                        return mix(0.175059, 0.122405, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.122405, 0.130886, s - 4.0);
                    } else {
                        return mix(0.130886, 0.149450, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.149450, 0.175209, s - 6.0);
                    } else {
                        return mix(0.175209, 0.206308, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.206308, 0.238815, s - 8.0);
                    } else {
                        return mix(0.238815, 0.271599, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.271599, 0.306402, s - 10.0);
                    } else {
                        return mix(0.306402, 0.348885, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.348885, 0.401335, s - 12.0);
                    } else {
                        return mix(0.401335, 0.453551, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.453551, 0.496813, s - 14.0);
                    } else {
                        return mix(0.496813, 0.525783, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.525783, 0.537822, s - 16.0);
                    } else {
                        return mix(0.537822, 0.543914, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.543914, 0.552605, s - 18.0);
                    } else {
                        return mix(0.552605, 0.576622, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.576622, 0.539232, s - 20.0);
                    } else {
                        return mix(0.539232, 0.491324, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.491324, 0.518226, s - 22.0);
                    } else {
                        return mix(0.518226, 0.574951, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.574951, 0.638455, s - 24.0);
                    } else {
                        return mix(0.638455, 0.709209, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.709209, 0.771333, s - 26.0);
                    } else {
                        return mix(0.771333, 0.798255, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.798255, 0.817562, s - 28.0);
                    } else {
                        return mix(0.817562, 0.863883, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.863883, 0.925476, s - 30.0);
                    } else {
                        return mix(0.925476, 0.746676, s - 31.0);
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
                        return mix(0.005095, 0.073586, s - 0.0);
                    } else {
                        return mix(0.073586, 0.129927, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.129927, 0.168556, s - 2.0);
                    } else {
                        return mix(0.168556, 0.127724, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.127724, 0.116995, s - 4.0);
                    } else {
                        return mix(0.116995, 0.149676, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.149676, 0.177095, s - 6.0);
                    } else {
                        return mix(0.177095, 0.205418, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.205418, 0.237496, s - 8.0);
                    } else {
                        return mix(0.237496, 0.275320, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.275320, 0.320378, s - 10.0);
                    } else {
                        return mix(0.320378, 0.367440, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.367440, 0.408490, s - 12.0);
                    } else {
                        return mix(0.408490, 0.443744, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.443744, 0.475654, s - 14.0);
                    } else {
                        return mix(0.475654, 0.503835, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.503835, 0.525127, s - 16.0);
                    } else {
                        return mix(0.525127, 0.541499, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.541499, 0.554560, s - 18.0);
                    } else {
                        return mix(0.554560, 0.574603, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.574603, 0.538244, s - 20.0);
                    } else {
                        return mix(0.538244, 0.495611, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.495611, 0.525585, s - 22.0);
                    } else {
                        return mix(0.525585, 0.586306, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.586306, 0.652992, s - 24.0);
                    } else {
                        return mix(0.652992, 0.721789, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.721789, 0.780706, s - 26.0);
                    } else {
                        return mix(0.780706, 0.807959, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.807959, 0.823517, s - 28.0);
                    } else {
                        return mix(0.823517, 0.863676, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.863676, 0.913442, s - 30.0);
                    } else {
                        return mix(0.913442, 0.746933, s - 31.0);
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
                        return mix(0.016480, 0.066439, s - 0.0);
                    } else {
                        return mix(0.066439, 0.115692, s - 1.0);
                    }
                } else {
                    if (s < 3.0) {
                        return mix(0.115692, 0.152687, s - 2.0);
                    } else {
                        return mix(0.152687, 0.143218, s - 3.0);
                    }
                }
            } else {
                if (s < 6.0) {
                    if (s < 5.0) {
                        return mix(0.143218, 0.133796, s - 4.0);
                    } else {
                        return mix(0.133796, 0.176854, s - 5.0);
                    }
                } else {
                    if (s < 7.0) {
                        return mix(0.176854, 0.206486, s - 6.0);
                    } else {
                        return mix(0.206486, 0.233810, s - 7.0);
                    }
                }
            }
        } else {
            if (s < 12.0) {
                if (s < 10.0) {
                    if (s < 9.0) {
                        return mix(0.233810, 0.263970, s - 8.0);
                    } else {
                        return mix(0.263970, 0.298833, s - 9.0);
                    }
                } else {
                    if (s < 11.0) {
                        return mix(0.298833, 0.341806, s - 10.0);
                    } else {
                        return mix(0.341806, 0.388305, s - 11.0);
                    }
                }
            } else {
                if (s < 14.0) {
                    if (s < 13.0) {
                        return mix(0.388305, 0.426925, s - 12.0);
                    } else {
                        return mix(0.426925, 0.460153, s - 13.0);
                    }
                } else {
                    if (s < 15.0) {
                        return mix(0.460153, 0.492688, s - 14.0);
                    } else {
                        return mix(0.492688, 0.524320, s - 15.0);
                    }
                }
            }
        }
    } else {
        if (s < 24.0) {
            if (s < 20.0) {
                if (s < 18.0) {
                    if (s < 17.0) {
                        return mix(0.524320, 0.550978, s - 16.0);
                    } else {
                        return mix(0.550978, 0.569942, s - 17.0);
                    }
                } else {
                    if (s < 19.0) {
                        return mix(0.569942, 0.580002, s - 18.0);
                    } else {
                        return mix(0.580002, 0.592594, s - 19.0);
                    }
                }
            } else {
                if (s < 22.0) {
                    if (s < 21.0) {
                        return mix(0.592594, 0.554401, s - 20.0);
                    } else {
                        return mix(0.554401, 0.513046, s - 21.0);
                    }
                } else {
                    if (s < 23.0) {
                        return mix(0.513046, 0.542175, s - 22.0);
                    } else {
                        return mix(0.542175, 0.600824, s - 23.0);
                    }
                }
            }
        } else {
            if (s < 28.0) {
                if (s < 26.0) {
                    if (s < 25.0) {
                        return mix(0.600824, 0.665665, s - 24.0);
                    } else {
                        return mix(0.665665, 0.732891, s - 25.0);
                    }
                } else {
                    if (s < 27.0) {
                        return mix(0.732891, 0.791325, s - 26.0);
                    } else {
                        return mix(0.791325, 0.824027, s - 27.0);
                    }
                }
            } else {
                if (s < 30.0) {
                    if (s < 29.0) {
                        return mix(0.824027, 0.846443, s - 28.0);
                    } else {
                        return mix(0.846443, 0.883118, s - 29.0);
                    }
                } else {
                    if (s < 31.0) {
                        return mix(0.883118, 0.920151, s - 30.0);
                    } else {
                        return mix(0.920151, 0.730802, s - 31.0);
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
                            return vec3(-0.14121, -0.22928, -0.10760);
                          } else {
                            return vec3(0.12237, -0.00311, -0.06972);
                          }
                        } else {
                          return vec3(0.14799, 0.03299, -0.02192);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(0.00757, -0.06702, -0.02490);
                        } else {
                          return vec3(-0.08346, -0.10538, -0.03115);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.10518, -0.08713, -0.00693);
                        } else {
                          return vec3(-0.10022, -0.06923, 0.04488);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.10508, -0.01804, -0.00340);
                        } else {
                          return vec3(-0.09829, -0.01459, 0.09188);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(-0.06631, -0.10844, -0.02206);
                          } else {
                            return vec3(0.15412, 0.05577, 0.04332);
                          }
                        } else {
                          return vec3(0.08999, 0.03130, 0.05469);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(-0.01161, -0.03838, -0.00017);
                        } else {
                          return vec3(-0.04788, -0.05537, -0.02410);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.04721, -0.04761, -0.00912);
                        } else {
                          return vec3(-0.03382, -0.03553, 0.03581);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.00846, 0.01745, -0.03311);
                        } else {
                          return vec3(0.00024, 0.01237, 0.06111);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.02430, -0.01998, 0.02680);
                        } else {
                          return vec3(0.00988, 0.01759, 0.06791);
                        }
                      } else {
                        return vec3(0.00055, -0.00589, 0.06427);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.01302, -0.00904, 0.01840);
                      } else {
                        return vec3(-0.03431, -0.00142, -0.01500);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.03399, 0.01937, -0.00559);
                      } else {
                        return vec3(-0.01866, 0.03704, 0.03648);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01066, 0.09245, -0.04066);
                      } else {
                        return vec3(0.01852, 0.08660, 0.05202);
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
                          return vec3(-0.02414, -0.03882, 0.03438);
                        } else {
                          return vec3(0.00000, -0.01281, 0.04834);
                        }
                      } else {
                        return vec3(0.00000, -0.02554, 0.05585);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.04523, 0.00446);
                      } else {
                        return vec3(0.00000, -0.02872, -0.02860);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.01417, -0.00495, -0.02298);
                      } else {
                        return vec3(-0.01903, 0.01193, 0.01531);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.01719, 0.05671, -0.06601);
                      } else {
                        return vec3(-0.01078, 0.04705, 0.02272);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.00136, -0.06601, 0.01923);
                        } else {
                          return vec3(0.00000, -0.02831, 0.02771);
                        }
                      } else {
                        return vec3(0.00000, -0.03982, 0.03650);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.06209, -0.00334);
                      } else {
                        return vec3(0.00000, -0.05853, -0.04625);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.04195, -0.04147);
                      } else {
                        return vec3(-0.00895, -0.03563, -0.00924);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.04956, -0.01256, -0.08748);
                      } else {
                        return vec3(-0.05411, -0.02218, 0.00252);
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
                          return vec3(-0.00101, -0.04670, 0.01051);
                        } else {
                          return vec3(0.00000, -0.00370, 0.01761);
                        }
                      } else {
                        return vec3(0.00000, -0.01439, 0.02763);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.03911, -0.00533);
                      } else {
                        return vec3(0.00000, -0.04368, -0.04199);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.03234, -0.05101);
                      } else {
                        return vec3(0.00000, -0.04044, -0.02640);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06533, -0.03528, -0.09461);
                      } else {
                        return vec3(-0.07360, -0.04036, 0.00408);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.01211, 0.01935, 0.01559);
                        } else {
                          return vec3(0.00000, 0.06466, 0.02096);
                        }
                      } else {
                        return vec3(0.00000, 0.05410, 0.03142);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.02565, 0.00048);
                      } else {
                        return vec3(-0.00142, 0.01089, -0.03534);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.01039, -0.04753);
                      } else {
                        return vec3(0.00000, 0.00494, -0.03311);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06535, -0.00563, -0.09326);
                      } else {
                        return vec3(-0.07649, -0.01927, 0.00162);
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
                          return vec3(-0.09681, 0.00000, 0.00917);
                        } else {
                          return vec3(0.00000, 0.02644, 0.00442);
                        }
                      } else {
                        return vec3(0.00000, 0.03487, 0.01045);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.01722, -0.01957);
                      } else {
                        return vec3(0.00000, -0.00955, -0.04716);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00878, -0.02650, -0.04828);
                      } else {
                        return vec3(-0.01682, -0.04478, -0.02635);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.02166, -0.07007);
                      } else {
                        return vec3(-0.01294, -0.06031, 0.00760);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.12346, 0.00000, 0.03814);
                        } else {
                          return vec3(0.00000, 0.01287, 0.02854);
                        }
                      } else {
                        return vec3(0.00000, 0.02308, 0.03052);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.00617, -0.00302);
                      } else {
                        return vec3(0.00000, 0.00000, -0.03219);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00061, 0.00209, -0.03335);
                      } else {
                        return vec3(-0.01491, 0.01583, -0.01537);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.00314, 0.07439, -0.07061);
                      } else {
                        return vec3(0.00000, 0.02389, -0.02811);
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
                            return vec3(-0.06143, -0.07739, -0.01939);
                          } else {
                            return vec3(0.08534, 0.00381, -0.02125);
                          }
                        } else {
                          return vec3(0.09694, 0.01600, -0.01092);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(0.02308, -0.01594, -0.02219);
                        } else {
                          return vec3(-0.02018, -0.00406, -0.01756);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.02798, 0.00000, 0.01473);
                        } else {
                          return vec3(-0.02125, 0.00000, 0.07086);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(-0.02762, 0.00000, 0.03347);
                        } else {
                          return vec3(-0.02177, 0.00000, 0.12797);
                        }
                      }
                    }
                  } else {
                    if (ib <= 4) {
                      if (ib <= 2) {
                        if (ib <= 1) {
                          if (ib <= 0) {
                            return vec3(-0.02997, -0.07014, -0.01125);
                          } else {
                            return vec3(-0.00521, -0.02742, -0.02521);
                          }
                        } else {
                          return vec3(-0.01361, -0.04135, -0.04025);
                        }
                      } else {
                        if (ib <= 3) {
                          return vec3(0.00868, -0.01711, -0.03198);
                        } else {
                          return vec3(-0.00284, -0.02576, -0.04334);
                        }
                      }
                    } else {
                      if (ib <= 6) {
                        if (ib <= 5) {
                          return vec3(-0.00441, -0.03208, -0.02969);
                        } else {
                          return vec3(0.00301, -0.03668, 0.01204);
                        }
                      } else {
                        if (ib <= 7) {
                          return vec3(0.01224, -0.04070, -0.06505);
                        } else {
                          return vec3(0.01980, -0.05256, 0.02769);
                        }
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.00845, -0.01258, -0.00617);
                        } else {
                          return vec3(0.00072, 0.01658, 0.00031);
                        }
                      } else {
                        return vec3(-0.02628, -0.00193, 0.00474);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00925, 0.01137, -0.02020);
                      } else {
                        return vec3(-0.00225, 0.03160, -0.02487);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00693, 0.04173, -0.00822);
                      } else {
                        return vec3(0.01929, 0.04441, 0.03375);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.04605, 0.05666, -0.03816);
                      } else {
                        return vec3(0.05517, 0.04993, 0.05884);
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
                          return vec3(0.02212, -0.01977, -0.00278);
                        } else {
                          return vec3(-0.00865, 0.00998, 0.01606);
                        }
                      } else {
                        return vec3(-0.00564, -0.00591, 0.02019);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00473, -0.02288, -0.02070);
                      } else {
                        return vec3(-0.00145, 0.00896, -0.02153);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00850, 0.02495, -0.00463);
                      } else {
                        return vec3(0.02298, 0.03285, 0.03826);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.04883, 0.05659, -0.01872);
                      } else {
                        return vec3(0.05344, 0.05238, 0.08336);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.02244, -0.03593, -0.00769);
                        } else {
                          return vec3(-0.02456, -0.02476, -0.00121);
                        }
                      } else {
                        return vec3(-0.01322, -0.02349, 0.02130);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02359, -0.03010, 0.00171);
                      } else {
                        return vec3(-0.00313, -0.02476, -0.02675);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00492, -0.01063, -0.00915);
                      } else {
                        return vec3(0.01861, -0.00025, 0.03635);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.02762, 0.02392, -0.00512);
                      } else {
                        return vec3(0.00658, -0.00282, 0.08558);
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
                          return vec3(0.00000, -0.01504, -0.00915);
                        } else {
                          return vec3(-0.04970, -0.01636, -0.01072);
                        }
                      } else {
                        return vec3(-0.03132, -0.00835, 0.01893);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.04723, -0.01605, 0.00709);
                      } else {
                        return vec3(-0.03968, -0.01726, -0.01662);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00128, -0.00640, -0.01384);
                      } else {
                        return vec3(0.00925, -0.00184, 0.03065);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.01590, -0.00559, -0.01629);
                      } else {
                        return vec3(-0.05686, -0.07311, 0.03409);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00000, 0.05060, 0.00154);
                        } else {
                          return vec3(-0.05201, 0.03759, -0.00990);
                        }
                      } else {
                        return vec3(-0.03471, 0.04453, 0.01738);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.06348, 0.03184, 0.00449);
                      } else {
                        return vec3(-0.07213, 0.02619, -0.01400);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.04312, 0.03280, -0.00737);
                      } else {
                        return vec3(-0.01192, 0.02914, 0.01599);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.06364, -0.00754, -0.05077);
                      } else {
                        return vec3(-0.07768, -0.09706, -0.04094);
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
                          return vec3(-0.02119, 0.00000, 0.00619);
                        } else {
                          return vec3(-0.07415, 0.00000, -0.03523);
                        }
                      } else {
                        return vec3(0.00000, 0.00725, -0.00884);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.00145, -0.01462);
                      } else {
                        return vec3(-0.01353, -0.00581, -0.01910);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.02462, -0.00875, -0.00108);
                      } else {
                        return vec3(-0.02151, -0.02340, 0.02627);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, -0.01179, -0.02316);
                      } else {
                        return vec3(0.00000, -0.08651, -0.00255);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.04464, 0.00000, 0.03653);
                        } else {
                          return vec3(-0.08396, 0.00000, -0.01498);
                        }
                      } else {
                        return vec3(0.00000, 0.00000, 0.00714);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.00743, -0.00214);
                      } else {
                        return vec3(0.00000, 0.02137, -0.01155);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00610, 0.04306, -0.00236);
                      } else {
                        return vec3(-0.00705, 0.06486, 0.02141);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00000, 0.10966, 0.00385);
                      } else {
                        return vec3(0.00000, 0.08534, 0.07287);
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
                          return vec3(0.00588, -0.01151, 0.01792);
                        } else {
                          return vec3(0.05157, 0.00000, 0.01280);
                        }
                      } else {
                        return vec3(0.06238, -0.00134, -0.00436);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.04090, 0.00000, -0.02319);
                      } else {
                        return vec3(0.02164, 0.00000, -0.02166);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02051, 0.00000, 0.01049);
                      } else {
                        return vec3(0.02659, 0.00000, 0.06667);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.00794, 0.00000, 0.03119);
                      } else {
                        return vec3(0.01108, 0.00000, 0.12462);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00690, -0.02418, 0.00336);
                        } else {
                          return vec3(0.01335, 0.00864, 0.01288);
                        }
                      } else {
                        return vec3(-0.00768, -0.04014, -0.03111);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00854, -0.02410, -0.04176);
                      } else {
                        return vec3(0.01862, -0.01297, -0.04211);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02820, -0.00884, -0.01779);
                      } else {
                        return vec3(0.03868, -0.01207, 0.02930);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.05050, -0.02526, -0.03399);
                      } else {
                        return vec3(0.05867, -0.03926, 0.05879);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01319, -0.02463, -0.01240);
                      } else {
                        return vec3(-0.04614, -0.00759, -0.02605);
                      }
                    } else {
                      return vec3(-0.00106, 0.00524, -0.01402);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03303, 0.02758, -0.02492);
                    } else {
                      return vec3(0.04465, 0.04182, -0.02797);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.05104, 0.04125, -0.01124);
                    } else {
                      return vec3(0.05673, 0.03127, 0.02688);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.06929, 0.00592, -0.05208);
                    } else {
                      return vec3(0.07940, -0.00278, 0.04504);
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
                        return vec3(0.03898, -0.02490, -0.01988);
                      } else {
                        return vec3(-0.01401, -0.00544, -0.01086);
                      }
                    } else {
                      return vec3(0.00633, -0.00749, 0.00707);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.01846, -0.00521, -0.03549);
                    } else {
                      return vec3(0.03371, 0.03362, -0.00760);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04588, 0.03110, 0.00327);
                    } else {
                      return vec3(0.05682, 0.03033, 0.04656);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08342, 0.03320, -0.00299);
                    } else {
                      return vec3(0.08982, 0.03321, 0.10687);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.08275, -0.03575, -0.02617);
                      } else {
                        return vec3(0.01373, -0.02288, -0.01177);
                      }
                    } else {
                      return vec3(0.00105, -0.01770, 0.02507);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00668, 0.00719, 0.03464);
                    } else {
                      return vec3(0.01703, -0.00209, -0.00806);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.03563, -0.00413, 0.00297);
                    } else {
                      return vec3(0.05475, 0.00721, 0.05747);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.07859, 0.03075, 0.03779);
                    } else {
                      return vec3(0.03920, -0.00200, 0.12567);
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
                        return vec3(0.07632, -0.01117, -0.02388);
                      } else {
                        return vec3(0.02470, -0.00433, -0.01076);
                      }
                    } else {
                      return vec3(-0.01289, -0.00957, 0.02399);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01292, -0.00765, 0.01655);
                    } else {
                      return vec3(-0.00738, -0.01008, -0.00769);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02279, -0.00550, -0.00362);
                    } else {
                      return vec3(0.04708, 0.00878, 0.05910);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.06223, 0.01614, 0.04117);
                    } else {
                      return vec3(-0.06120, -0.15681, -0.04126);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.06202, 0.05525, -0.01059);
                      } else {
                        return vec3(0.01835, 0.05196, -0.00647);
                      }
                    } else {
                      return vec3(-0.03216, 0.02994, 0.01516);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03009, 0.02618, 0.00442);
                    } else {
                      return vec3(-0.03293, 0.02395, -0.01116);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.01045, 0.02985, 0.00088);
                    } else {
                      return vec3(0.01821, 0.02728, 0.03373);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00453, -0.02283, -0.04559);
                    } else {
                      return vec3(-0.09421, -0.23749, -0.23428);
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
                        return vec3(0.02921, 0.01842, -0.00041);
                      } else {
                        return vec3(-0.00707, -0.00045, -0.02414);
                      }
                    } else {
                      return vec3(-0.05123, -0.02630, -0.02111);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00202, -0.02856, -0.01940);
                    } else {
                      return vec3(0.00644, -0.02146, -0.01734);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01173, -0.01766, 0.00579);
                    } else {
                      return vec3(0.01856, -0.03247, 0.03187);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.05836, -0.02053, -0.02540);
                    } else {
                      return vec3(0.03170, -0.08956, -0.02297);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01617, 0.00000, 0.02942);
                      } else {
                        return vec3(-0.04725, 0.00000, -0.00495);
                      }
                    } else {
                      return vec3(-0.09345, 0.00000, -0.01018);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03074, 0.00000, -0.01254);
                    } else {
                      return vec3(-0.02469, 0.02936, -0.01855);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02365, 0.06152, -0.00968);
                    } else {
                      return vec3(-0.01665, 0.06330, 0.01524);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03971, 0.11613, 0.01864);
                    } else {
                      return vec3(0.06381, 0.11007, 0.11276);
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
                          return vec3(-0.00342, -0.01199, 0.00644);
                        } else {
                          return vec3(0.03131, 0.00000, 0.01730);
                        }
                      } else {
                        return vec3(0.02870, 0.00000, 0.02106);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.04496, 0.00000, -0.00921);
                      } else {
                        return vec3(0.02665, 0.00000, -0.02206);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.02288, 0.00000, 0.00001);
                      } else {
                        return vec3(0.02415, 0.00000, 0.05071);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.02133, 0.00000, 0.00975);
                      } else {
                        return vec3(-0.02363, 0.00000, 0.10236);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00331, -0.00356, 0.00537);
                        } else {
                          return vec3(-0.03016, 0.01217, 0.01400);
                        }
                      } else {
                        return vec3(-0.03608, -0.01597, -0.00012);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.03103, -0.04137, -0.04172);
                      } else {
                        return vec3(-0.01197, -0.01962, -0.04278);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00273, -0.00897, -0.01618);
                      } else {
                        return vec3(0.01344, -0.01050, 0.03220);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01750, -0.03008, -0.02265);
                      } else {
                        return vec3(0.02517, -0.04589, 0.06911);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.01439, 0.01248, 0.00305);
                      } else {
                        return vec3(-0.08700, 0.01748, -0.00365);
                      }
                    } else {
                      return vec3(-0.07808, 0.01331, 0.00411);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05693, -0.00093, -0.03934);
                    } else {
                      return vec3(-0.01196, 0.03381, -0.02864);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00047, 0.04241, -0.00071);
                    } else {
                      return vec3(0.00850, 0.03818, 0.04383);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03192, 0.02034, -0.01789);
                    } else {
                      return vec3(0.04626, 0.01124, 0.07685);
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
                        return vec3(-0.00376, -0.02878, -0.00448);
                      } else {
                        return vec3(-0.11230, -0.03286, -0.01762);
                      }
                    } else {
                      return vec3(-0.12272, -0.03382, -0.00501);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01218, 0.01563, 0.00390);
                    } else {
                      return vec3(0.05292, 0.04410, 0.00868);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.05586, 0.03324, 0.02247);
                    } else {
                      return vec3(0.05655, 0.02327, 0.06320);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.07803, -0.00214, 0.00094);
                    } else {
                      return vec3(0.08872, -0.00838, 0.10097);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.04813, -0.03948, -0.01864);
                      } else {
                        return vec3(-0.02440, -0.02748, -0.00828);
                      }
                    } else {
                      return vec3(-0.04413, -0.02210, 0.02539);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00567, 0.01413, 0.04477);
                    } else {
                      return vec3(0.00430, -0.00276, -0.00718);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.02488, -0.00397, 0.01381);
                    } else {
                      return vec3(0.03478, 0.00139, 0.07215);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.06216, 0.00598, 0.04854);
                    } else {
                      return vec3(0.04392, -0.01910, 0.12774);
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
                        return vec3(0.08979, -0.01397, -0.02003);
                      } else {
                        return vec3(0.04389, 0.00480, -0.00258);
                      }
                    } else {
                      return vec3(0.01208, 0.00291, 0.03194);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00757, 0.00608, 0.03767);
                    } else {
                      return vec3(-0.00668, -0.00450, -0.00125);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00864, -0.01365, -0.00645);
                    } else {
                      return vec3(0.01290, -0.00604, 0.06101);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04723, 0.00679, 0.05296);
                    } else {
                      return vec3(-0.05084, -0.07287, 0.01340);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.11662, 0.05292, -0.00972);
                      } else {
                        return vec3(0.06699, 0.06390, 0.00222);
                      }
                    } else {
                      return vec3(0.01404, 0.04658, 0.02685);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02057, 0.03080, 0.02335);
                    } else {
                      return vec3(-0.03508, 0.02482, -0.00667);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03549, 0.01955, -0.00685);
                    } else {
                      return vec3(-0.02669, -0.00230, 0.01236);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01175, -0.03993, -0.04674);
                    } else {
                      return vec3(-0.06718, 0.01653, -0.01100);
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
                        return vec3(0.06717, 0.01172, 0.00134);
                      } else {
                        return vec3(0.06637, 0.00890, -0.00780);
                      }
                    } else {
                      return vec3(0.01692, -0.02670, 0.00065);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02771, -0.05916, -0.01162);
                    } else {
                      return vec3(-0.00623, -0.04152, -0.02001);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00142, -0.03630, -0.00713);
                    } else {
                      return vec3(0.00749, -0.05630, 0.00915);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04281, -0.02227, -0.03477);
                    } else {
                      return vec3(0.04241, -0.01350, 0.04354);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.03487, 0.01633, 0.02883);
                      } else {
                        return vec3(0.02704, 0.02430, 0.00994);
                      }
                    } else {
                      return vec3(-0.03394, 0.00165, 0.01063);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.08278, 0.00000, -0.00984);
                    } else {
                      return vec3(-0.05292, 0.03433, -0.02694);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.04069, 0.05345, -0.02619);
                    } else {
                      return vec3(-0.02514, 0.05238, 0.00091);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02725, 0.11235, 0.00075);
                    } else {
                      return vec3(0.05519, 0.08924, 0.08197);
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
                          return vec3(-0.06116, -0.02973, 0.00000);
                        } else {
                          return vec3(-0.01230, 0.00000, 0.00854);
                        }
                      } else {
                        return vec3(-0.02027, 0.00000, 0.03425);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.02664, 0.00000, 0.01583);
                      } else {
                        return vec3(0.01999, 0.00000, -0.00855);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00870, 0.00000, -0.00299);
                      } else {
                        return vec3(0.00057, 0.00000, 0.03703);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.08280, 0.00000, -0.01662);
                      } else {
                        return vec3(-0.09208, 0.00000, 0.07474);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(-0.02817, -0.00616, -0.00228);
                        } else {
                          return vec3(-0.09806, -0.01133, 0.00412);
                        }
                      } else {
                        return vec3(-0.09416, -0.01851, 0.01658);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.10068, -0.03279, -0.00953);
                      } else {
                        return vec3(-0.06113, -0.03370, -0.03619);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.04531, -0.02047, -0.01663);
                      } else {
                        return vec3(-0.03943, -0.02189, 0.02755);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.05564, -0.03675, -0.02690);
                      } else {
                        return vec3(-0.05138, -0.04230, 0.06236);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.03994, 0.03247, 0.00919);
                      } else {
                        return vec3(-0.13883, 0.01756, 0.00448);
                      }
                    } else {
                      return vec3(-0.16765, -0.00533, 0.00767);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.13059, 0.00387, -0.01515);
                    } else {
                      return vec3(-0.09617, 0.01445, -0.03381);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08831, 0.02817, -0.00245);
                    } else {
                      return vec3(-0.08068, 0.02950, 0.04364);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.05433, 0.02166, -0.01062);
                    } else {
                      return vec3(-0.03951, 0.00918, 0.07716);
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
                        return vec3(-0.03610, 0.00155, 0.01519);
                      } else {
                        return vec3(-0.18037, -0.00951, 0.01344);
                      }
                    } else {
                      return vec3(-0.20292, -0.04542, -0.01108);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05402, 0.01283, 0.01310);
                    } else {
                      return vec3(-0.07333, 0.00778, -0.01753);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.09081, 0.00847, 0.01817);
                    } else {
                      return vec3(-0.07780, 0.01213, 0.06580);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02185, 0.01287, 0.01368);
                    } else {
                      return vec3(-0.00589, 0.00208, 0.09971);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.05402, -0.03234, 0.02016);
                      } else {
                        return vec3(-0.14062, -0.02204, 0.02141);
                      }
                    } else {
                      return vec3(-0.08220, -0.01583, 0.02642);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03693, -0.00800, 0.01094);
                    } else {
                      return vec3(-0.00009, 0.01443, 0.01799);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00370, 0.01420, 0.04680);
                    } else {
                      return vec3(0.01112, 0.01274, 0.09713);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04678, 0.00560, 0.05868);
                    } else {
                      return vec3(0.04877, -0.00507, 0.13781);
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
                        return vec3(-0.01300, -0.01402, 0.01112);
                      } else {
                        return vec3(-0.01417, 0.01538, 0.01835);
                      }
                    } else {
                      return vec3(0.00241, 0.01919, 0.03738);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.02552, 0.01010, 0.02768);
                    } else {
                      return vec3(0.00047, 0.02457, 0.03018);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.04664, -0.00278, 0.00378);
                    } else {
                      return vec3(-0.03227, -0.01072, 0.05615);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02507, 0.03281, 0.07862);
                    } else {
                      return vec3(0.00668, 0.06953, 0.18732);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.04658, 0.05204, 0.01178);
                      } else {
                        return vec3(0.03286, 0.07188, 0.01907);
                      }
                    } else {
                      return vec3(-0.01196, 0.05800, 0.03580);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07825, 0.03459, 0.02012);
                    } else {
                      return vec3(-0.04975, 0.04458, 0.01821);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.07963, 0.02194, -0.01168);
                    } else {
                      return vec3(-0.09615, -0.01344, -0.00980);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.04145, -0.02232, -0.03875);
                    } else {
                      return vec3(-0.00177, 0.16179, 0.18884);
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
                        return vec3(0.00602, 0.00198, 0.01885);
                      } else {
                        return vec3(0.04149, 0.00955, 0.01146);
                      }
                    } else {
                      return vec3(0.00328, -0.01667, 0.01812);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.06289, -0.04956, -0.00398);
                    } else {
                      return vec3(-0.05868, -0.05207, -0.00831);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.05708, -0.05162, -0.02172);
                    } else {
                      return vec3(-0.05845, -0.07027, -0.01451);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.04127, -0.02086, -0.05386);
                    } else {
                      return vec3(-0.00889, 0.03458, 0.09093);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00667, 0.05095, 0.04309);
                      } else {
                        return vec3(0.01207, 0.06360, 0.02673);
                      }
                    } else {
                      return vec3(-0.04214, 0.04565, 0.02812);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.11191, 0.02867, 0.00307);
                    } else {
                      return vec3(-0.11011, 0.04298, -0.00640);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.09512, 0.04957, -0.02227);
                    } else {
                      return vec3(-0.08089, 0.05202, -0.00361);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.06352, 0.10510, -0.03737);
                    } else {
                      return vec3(-0.04775, 0.06864, 0.02708);
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
                          return vec3(-0.04667, -0.04609, 0.00000);
                        } else {
                          return vec3(0.01159, 0.00000, -0.01159);
                        }
                      } else {
                        return vec3(0.00637, 0.00000, 0.02485);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.00454, 0.00000, 0.01749);
                      } else {
                        return vec3(0.02138, 0.00000, -0.00378);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.07340, 0.00000, -0.00020);
                      } else {
                        return vec3(0.05709, 0.00000, 0.03141);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.04952, 0.00000, -0.03196);
                      } else {
                        return vec3(-0.06310, -0.00197, 0.05715);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.00884, -0.01403, 0.00000);
                        } else {
                          return vec3(-0.08338, -0.02518, -0.02544);
                        }
                      } else {
                        return vec3(-0.05648, -0.01968, 0.02131);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(-0.05989, -0.03275, 0.00685);
                      } else {
                        return vec3(-0.04198, -0.03527, -0.02203);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(-0.00024, -0.02756, -0.01868);
                      } else {
                        return vec3(0.00043, -0.01590, 0.01972);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(-0.03143, -0.02807, -0.03854);
                      } else {
                        return vec3(-0.03305, -0.03405, 0.04690);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.00549, 0.03380, 0.00000);
                      } else {
                        return vec3(-0.05504, 0.02008, 0.00225);
                      }
                    } else {
                      return vec3(-0.08077, 0.00203, 0.02530);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07476, 0.00769, -0.00100);
                    } else {
                      return vec3(-0.06589, 0.01847, -0.01777);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.05889, 0.02062, -0.01259);
                    } else {
                      return vec3(-0.05541, 0.02149, 0.02979);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.04055, 0.01336, -0.02441);
                    } else {
                      return vec3(-0.03270, -0.00525, 0.05682);
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
                        return vec3(-0.01315, 0.00362, 0.00256);
                      } else {
                        return vec3(-0.09144, 0.00401, 0.01309);
                      }
                    } else {
                      return vec3(-0.02483, -0.00865, -0.02771);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02375, 0.01762, 0.00849);
                    } else {
                      return vec3(-0.03219, 0.01583, 0.00075);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.09377, -0.00283, -0.00161);
                    } else {
                      return vec3(-0.08014, 0.00144, 0.04004);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02636, 0.00782, -0.00640);
                    } else {
                      return vec3(-0.01193, -0.00391, 0.07677);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.04597, -0.04558, 0.00829);
                      } else {
                        return vec3(-0.14976, -0.02383, 0.02393);
                      }
                    } else {
                      return vec3(0.08460, 0.02922, 0.01502);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.13550, 0.04313, 0.02437);
                    } else {
                      return vec3(0.00915, 0.00241, 0.03511);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.05668, -0.00939, 0.02634);
                    } else {
                      return vec3(-0.03726, -0.01543, 0.05622);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02007, -0.00601, 0.02558);
                    } else {
                      return vec3(0.04251, 0.00491, 0.13108);
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
                        return vec3(-0.06034, -0.04203, 0.01489);
                      } else {
                        return vec3(-0.07366, -0.00928, 0.01668);
                      }
                    } else {
                      return vec3(-0.00024, 0.01340, 0.02383);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00578, 0.00859, 0.00577);
                    } else {
                      return vec3(-0.07161, -0.02413, -0.03015);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.00230, -0.00084, -0.00099);
                    } else {
                      return vec3(0.00416, -0.01826, 0.04156);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08893, 0.02416, 0.06239);
                    } else {
                      return vec3(0.11906, 0.05498, 0.18785);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.01160, 0.02167, 0.00443);
                      } else {
                        return vec3(-0.00770, 0.03736, 0.00739);
                      }
                    } else {
                      return vec3(-0.05176, 0.03155, 0.02275);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.12128, 0.00939, -0.00581);
                    } else {
                      return vec3(-0.11749, 0.00353, -0.03671);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.07550, -0.01304, -0.05462);
                    } else {
                      return vec3(-0.09601, -0.03170, -0.03901);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03037, 0.04293, 0.02131);
                    } else {
                      return vec3(0.06131, 0.06835, 0.14024);
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
                        return vec3(-0.01605, -0.02531, 0.00565);
                      } else {
                        return vec3(0.02839, -0.02028, -0.00249);
                      }
                    } else {
                      return vec3(-0.00537, -0.03842, 0.00687);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.06645, -0.05947, -0.01809);
                    } else {
                      return vec3(-0.07874, -0.06617, -0.03823);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03758, -0.06443, -0.02947);
                    } else {
                      return vec3(-0.04092, -0.07023, -0.01606);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.04980, -0.02157, -0.06706);
                    } else {
                      return vec3(-0.01412, 0.00501, 0.06539);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.00288, 0.08306, 0.02745);
                      } else {
                        return vec3(0.04829, 0.09012, 0.01304);
                      }
                    } else {
                      return vec3(0.00246, 0.06846, 0.01821);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.07322, 0.04737, -0.00278);
                    } else {
                      return vec3(-0.08736, 0.06167, -0.00373);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03982, 0.07744, 0.01780);
                    } else {
                      return vec3(-0.04444, 0.06454, 0.01645);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.06711, 0.10032, -0.05001);
                    } else {
                      return vec3(-0.05408, 0.08203, 0.03563);
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
                          return vec3(0.00553, -0.05647, 0.00000);
                        } else {
                          return vec3(0.07693, 0.00000, -0.02536);
                        }
                      } else {
                        return vec3(0.07612, 0.00000, 0.01136);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.06630, 0.00000, 0.00771);
                      } else {
                        return vec3(0.07986, 0.00000, -0.00973);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.11957, 0.00000, -0.00421);
                      } else {
                        return vec3(0.14902, 0.00000, 0.02940);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.02624, 0.00000, -0.04173);
                      } else {
                        return vec3(0.00958, -0.00570, 0.04358);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.08312, -0.01823, 0.00000);
                        } else {
                          return vec3(-0.01725, -0.03248, -0.05154);
                        }
                      } else {
                        return vec3(0.03714, -0.01965, 0.02388);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.02986, -0.03647, 0.00944);
                      } else {
                        return vec3(0.02950, -0.04077, -0.01953);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.05796, -0.02133, -0.01931);
                      } else {
                        return vec3(0.08354, -0.00551, 0.01050);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.03958, -0.01778, -0.05148);
                      } else {
                        return vec3(0.03100, -0.02401, 0.03057);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.08492, 0.03268, 0.00000);
                      } else {
                        return vec3(0.04903, 0.02507, -0.02675);
                      }
                    } else {
                      return vec3(0.03466, 0.01021, 0.03625);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.02091, 0.01293, 0.01766);
                    } else {
                      return vec3(0.00931, 0.01799, -0.01031);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01272, 0.02018, -0.01490);
                    } else {
                      return vec3(0.02415, 0.01637, 0.00975);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02438, 0.00430, -0.04473);
                    } else {
                      return vec3(0.02148, -0.01993, 0.03509);
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
                        return vec3(0.08023, -0.00298, -0.00620);
                      } else {
                        return vec3(0.06285, 0.01075, -0.01402);
                      }
                    } else {
                      return vec3(0.06758, 0.00781, 0.01267);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.07223, 0.01318, 0.03143);
                    } else {
                      return vec3(0.02908, 0.00819, 0.00063);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.01574, -0.00253, -0.01291);
                    } else {
                      return vec3(-0.02089, -0.01074, 0.00161);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02249, -0.00436, -0.03852);
                    } else {
                      return vec3(0.03034, -0.01807, 0.04969);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.03342, -0.07117, -0.01617);
                      } else {
                        return vec3(-0.02518, -0.04377, -0.00872);
                      }
                    } else {
                      return vec3(0.02660, -0.00863, 0.01855);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.08262, -0.00572, -0.00053);
                    } else {
                      return vec3(0.04043, -0.03206, -0.00059);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.02349, -0.04823, -0.02067);
                    } else {
                      return vec3(-0.03595, -0.06050, -0.01286);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.04413, -0.03231, -0.02475);
                    } else {
                      return vec3(0.07752, -0.01824, 0.09254);
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
                        return vec3(0.01346, -0.08001, -0.01280);
                      } else {
                        return vec3(-0.10833, -0.10187, -0.02793);
                      }
                    } else {
                      return vec3(-0.11089, -0.04867, 0.00990);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.04367, -0.02442, -0.01597);
                    } else {
                      return vec3(-0.06799, -0.07842, -0.07792);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.07266, -0.12117, -0.10688);
                    } else {
                      return vec3(-0.06127, -0.10077, -0.05883);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.08893, -0.01331, -0.00230);
                    } else {
                      return vec3(0.14861, 0.02133, 0.13531);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.04623, -0.01085, -0.00422);
                      } else {
                        return vec3(-0.07476, -0.06220, -0.04533);
                      }
                    } else {
                      return vec3(-0.15078, -0.04859, -0.01598);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.16430, -0.00041, -0.01529);
                    } else {
                      return vec3(-0.14411, -0.03115, -0.07831);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.14572, -0.10431, -0.14860);
                    } else {
                      return vec3(-0.04279, -0.04476, -0.05429);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.13318, 0.05836, 0.02592);
                    } else {
                      return vec3(0.15827, 0.04867, 0.10589);
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
                        return vec3(0.01267, -0.05978, -0.01542);
                      } else {
                        return vec3(0.05579, -0.05868, -0.04694);
                      }
                    } else {
                      return vec3(0.01869, -0.06087, -0.02397);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.03233, -0.05618, -0.02400);
                    } else {
                      return vec3(-0.03335, -0.05066, -0.03144);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.00643, -0.05694, -0.03253);
                    } else {
                      return vec3(0.04988, -0.04555, 0.01408);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.01253, 0.00181, -0.04450);
                    } else {
                      return vec3(0.00597, -0.03100, 0.02214);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.06545, 0.10852, -0.01020);
                      } else {
                        return vec3(0.15995, 0.11089, -0.02482);
                      }
                    } else {
                      return vec3(0.12747, 0.08367, -0.01078);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03076, 0.05628, -0.01774);
                    } else {
                      return vec3(-0.00522, 0.06838, 0.00481);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04644, 0.10938, 0.05234);
                    } else {
                      return vec3(0.06942, 0.10895, 0.07303);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02569, 0.09571, -0.04549);
                    } else {
                      return vec3(0.03873, 0.11200, 0.07113);
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
                          return vec3(0.00000, -0.06977, 0.00000);
                        } else {
                          return vec3(0.00000, -0.00826, -0.03022);
                        }
                      } else {
                        return vec3(0.02413, 0.00000, 0.00216);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.01857, 0.00000, -0.00451);
                      } else {
                        return vec3(0.00599, 0.00000, -0.01667);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00925, 0.00000, -0.00321);
                      } else {
                        return vec3(0.02003, 0.00000, 0.03575);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.05003, 0.00000, -0.00287);
                      } else {
                        return vec3(0.02935, 0.00000, 0.07808);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.01294, 0.01155, 0.00000);
                        } else {
                          return vec3(-0.02766, -0.05731, -0.05112);
                        }
                      } else {
                        return vec3(0.00741, -0.04474, 0.00228);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.01695, -0.04567, 0.00511);
                      } else {
                        return vec3(0.00701, -0.03462, -0.00845);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00965, -0.01099, -0.00118);
                      } else {
                        return vec3(0.01830, 0.00000, 0.03219);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.06517, 0.00000, -0.01596);
                      } else {
                        return vec3(0.04939, 0.00000, 0.06514);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.06963, 0.08795, 0.00000);
                      } else {
                        return vec3(0.01003, 0.03698, -0.04135);
                      }
                    } else {
                      return vec3(-0.03792, -0.01024, 0.01146);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00330, 0.00949, 0.03080);
                    } else {
                      return vec3(-0.01055, 0.02092, 0.00817);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.01674, 0.02783, 0.00603);
                    } else {
                      return vec3(-0.01603, 0.02634, 0.03319);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02691, 0.04359, -0.02271);
                    } else {
                      return vec3(0.01658, 0.01744, 0.06080);
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
                        return vec3(0.10470, 0.06712, 0.00000);
                      } else {
                        return vec3(0.09276, 0.05252, -0.02954);
                      }
                    } else {
                      return vec3(0.05225, 0.02750, 0.07446);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.01207, -0.01350, 0.05882);
                    } else {
                      return vec3(-0.01301, -0.00049, 0.01674);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.03683, 0.00203, -0.00206);
                    } else {
                      return vec3(-0.04775, 0.00008, 0.01901);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.02583, 0.02789, -0.04399);
                    } else {
                      return vec3(-0.02293, 0.01309, 0.05105);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.05719, -0.00764, 0.00000);
                      } else {
                        return vec3(0.02594, -0.01704, -0.01591);
                      }
                    } else {
                      return vec3(0.04241, -0.00351, 0.03598);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00477, -0.02703, 0.03030);
                    } else {
                      return vec3(-0.02746, -0.05533, 0.00443);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.06088, -0.06872, -0.02987);
                    } else {
                      return vec3(-0.07375, -0.06601, -0.00458);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.07177, -0.02436, -0.06377);
                    } else {
                      return vec3(-0.04012, -0.01539, 0.05513);
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
                        return vec3(0.02805, -0.02589, 0.00000);
                      } else {
                        return vec3(-0.14313, -0.13761, -0.05647);
                      }
                    } else {
                      return vec3(-0.21930, -0.13230, -0.00679);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.06251, -0.00718, 0.01231);
                    } else {
                      return vec3(-0.08789, -0.08286, -0.06122);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08183, -0.11313, -0.06077);
                    } else {
                      return vec3(-0.09798, -0.09504, -0.02022);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.09187, -0.02953, -0.06516);
                    } else {
                      return vec3(-0.02638, 0.00333, 0.07296);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.03611, 0.02804, 0.00000);
                      } else {
                        return vec3(-0.10178, -0.08183, -0.08574);
                      }
                    } else {
                      return vec3(-0.22475, -0.03778, 0.00147);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.16987, 0.05231, 0.03884);
                    } else {
                      return vec3(-0.01723, 0.03323, -0.00703);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08160, -0.03061, -0.03148);
                    } else {
                      return vec3(-0.10841, -0.05331, -0.00038);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(-0.05747, 0.05301, -0.02080);
                    } else {
                      return vec3(-0.04299, 0.04036, 0.05996);
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
                        return vec3(-0.15376, -0.00173, 0.00000);
                      } else {
                        return vec3(-0.01025, -0.00833, -0.04153);
                      }
                    } else {
                      return vec3(-0.01202, -0.00992, -0.02769);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.15759, -0.04218, -0.00460);
                    } else {
                      return vec3(-0.09637, -0.01725, -0.01498);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.08816, -0.02522, -0.02013);
                    } else {
                      return vec3(-0.09209, -0.04778, -0.00393);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.05164, 0.04190, 0.01537);
                    } else {
                      return vec3(0.02481, -0.00864, 0.03438);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(-0.08180, 0.18342, 0.00000);
                      } else {
                        return vec3(0.12166, 0.17519, -0.00735);
                      }
                    } else {
                      return vec3(0.11458, 0.11853, -0.00221);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.00999, 0.05732, -0.03266);
                    } else {
                      return vec3(-0.10279, 0.04069, -0.03408);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(-0.06201, 0.06124, 0.02166);
                    } else {
                      return vec3(-0.02800, 0.09136, 0.08835);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02024, 0.14661, 0.04049);
                    } else {
                      return vec3(0.00670, 0.07565, 0.05962);
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
                          return vec3(0.00000, -0.06861, 0.00000);
                        } else {
                          return vec3(0.00000, -0.00937, -0.03438);
                        }
                      } else {
                        return vec3(0.00000, 0.00000, -0.02031);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, 0.00000, -0.02712);
                      } else {
                        return vec3(0.00000, 0.00000, -0.03370);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, 0.00000, -0.01482);
                      } else {
                        return vec3(0.00000, 0.00000, 0.02534);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.01277, 0.00000, -0.00774);
                      } else {
                        return vec3(0.01524, 0.00000, 0.07311);
                      }
                    }
                  }
                } else {
                  if (ib <= 4) {
                    if (ib <= 2) {
                      if (ib <= 1) {
                        if (ib <= 0) {
                          return vec3(0.02761, 0.01261, 0.00000);
                        } else {
                          return vec3(0.00000, -0.07331, -0.06907);
                        }
                      } else {
                        return vec3(0.00000, -0.06235, -0.02214);
                      }
                    } else {
                      if (ib <= 3) {
                        return vec3(0.00000, -0.05640, -0.01699);
                      } else {
                        return vec3(0.00000, -0.03383, -0.02539);
                      }
                    }
                  } else {
                    if (ib <= 6) {
                      if (ib <= 5) {
                        return vec3(0.00000, -0.01002, -0.01642);
                      } else {
                        return vec3(0.00696, 0.00000, 0.01619);
                      }
                    } else {
                      if (ib <= 7) {
                        return vec3(0.05735, 0.00000, -0.02566);
                      } else {
                        return vec3(0.06226, 0.00000, 0.05607);
                      }
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.19978, 0.08843, 0.00000);
                      } else {
                        return vec3(0.08068, 0.02688, -0.04537);
                      }
                    } else {
                      return vec3(0.00000, -0.02835, 0.00276);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.00839, -0.01364, 0.00646);
                    } else {
                      return vec3(0.00746, -0.00338, -0.01623);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.01111, 0.00359, -0.02128);
                    } else {
                      return vec3(0.02009, 0.00269, 0.00528);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.06591, 0.02509, -0.04164);
                    } else {
                      return vec3(0.07067, 0.00411, 0.04470);
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
                        return vec3(0.24639, 0.06343, 0.00000);
                      } else {
                        return vec3(0.20230, 0.03369, -0.03408);
                      }
                    } else {
                      return vec3(0.13996, -0.00402, 0.02545);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.04947, -0.05123, 0.02964);
                    } else {
                      return vec3(0.04777, -0.03677, -0.01901);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04264, -0.03249, -0.04349);
                    } else {
                      return vec3(0.04270, -0.03144, -0.02128);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.05944, 0.00344, -0.07337);
                    } else {
                      return vec3(0.06142, -0.00991, 0.02210);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.19533, -0.02261, 0.00000);
                      } else {
                        return vec3(0.15184, -0.04359, -0.04685);
                      }
                    } else {
                      return vec3(0.12536, -0.04773, 0.01466);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.08433, -0.05354, 0.02007);
                    } else {
                      return vec3(0.06931, -0.06835, -0.00734);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.05750, -0.08269, -0.05282);
                    } else {
                      return vec3(0.04713, -0.08865, -0.03567);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.03057, -0.05213, -0.09627);
                    } else {
                      return vec3(0.04360, -0.05643, 0.00778);
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
                        return vec3(0.14214, -0.07469, 0.00000);
                      } else {
                        return vec3(0.05453, -0.07334, -0.06428);
                      }
                    } else {
                      return vec3(0.00874, -0.03700, 0.01266);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.03998, -0.02354, 0.00540);
                    } else {
                      return vec3(0.10690, -0.01436, -0.00433);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.12095, -0.03496, 0.00202);
                    } else {
                      return vec3(0.05760, -0.07357, -0.00189);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.00220, -0.05469, -0.08883);
                    } else {
                      return vec3(0.03425, -0.04694, 0.02075);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.14927, -0.02842, 0.00000);
                      } else {
                        return vec3(0.13304, 0.01372, -0.08044);
                      }
                    } else {
                      return vec3(-0.03778, 0.06282, 0.02287);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.05333, 0.03796, 0.01333);
                    } else {
                      return vec3(0.13781, 0.06846, -0.00387);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.14024, 0.13876, 0.11184);
                    } else {
                      return vec3(0.12567, 0.04676, 0.10306);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.02166, 0.02138, -0.03998);
                    } else {
                      return vec3(0.06747, 0.05078, 0.07976);
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
                        return vec3(-0.03390, -0.03602, 0.00000);
                      } else {
                        return vec3(0.20709, 0.00312, -0.04363);
                      }
                    } else {
                      return vec3(0.16809, 0.01208, -0.02240);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(-0.12331, -0.05468, 0.00535);
                    } else {
                      return vec3(0.09117, -0.02696, -0.07668);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.06434, 0.05167, 0.03962);
                    } else {
                      return vec3(0.07320, 0.02480, 0.09527);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.20322, 0.06660, 0.06028);
                    } else {
                      return vec3(0.18750, 0.07628, 0.13928);
                    }
                  }
                }
              } else {
                if (ib <= 4) {
                  if (ib <= 2) {
                    if (ib <= 1) {
                      if (ib <= 0) {
                        return vec3(0.05012, 0.18557, 0.00000);
                      } else {
                        return vec3(0.22661, 0.17443, -0.02996);
                      }
                    } else {
                      return vec3(0.23285, 0.12281, -0.04892);
                    }
                  } else {
                    if (ib <= 3) {
                      return vec3(0.12484, 0.05133, -0.06423);
                    } else {
                      return vec3(0.01963, 0.02605, -0.06689);
                    }
                  }
                } else {
                  if (ib <= 6) {
                    if (ib <= 5) {
                      return vec3(0.04401, 0.04059, 0.00788);
                    } else {
                      return vec3(0.04867, 0.06668, 0.16694);
                    }
                  } else {
                    if (ib <= 7) {
                      return vec3(0.17811, 0.17889, 0.16422);
                    } else {
                      return vec3(-0.05468, -0.06241, -0.10691);
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
    vec3 outCol = vec3(0.166469, 0.254356, 0.122527);
    outCol += (r) * vec3(0.727181, -1.102908, -0.355351);
    outCol += (g) * vec3(-0.262453, 0.719967, -0.424315);
    outCol += (b) * vec3(-0.990521, -0.518949, 0.605547);
    outCol += (rr) * vec3(1.319131, 3.361025, -0.050457);
    outCol += (gg) * vec3(0.320413, 0.806054, 0.731705);
    outCol += (bb) * vec3(2.604583, 2.920058, 0.154425);
    outCol += (rg) * vec3(1.813525, 2.156970, 1.845919);
    outCol += (rb) * vec3(2.085519, 0.133595, 0.016894);
    outCol += (gb) * vec3(2.183595, -0.184683, 1.355458);
    outCol += (rrr) * vec3(-0.565169, -3.657799, -1.246274);
    outCol += (ggg) * vec3(-0.008435, 0.175046, -0.171347);
    outCol += (bbb) * vec3(-6.860185, -5.302352, 0.433134);
    outCol += (rrg) * vec3(0.372695, -3.608060, 0.231726);
    outCol += (rrb) * vec3(-0.095677, 0.717578, 3.251238);
    outCol += (ggr) * vec3(-1.093630, -0.265315, -1.195785);
    outCol += (ggb) * vec3(0.252178, 2.397342, 0.144109);
    outCol += (bbr) * vec3(2.281247, 1.295797, 0.785679);
    outCol += (bbg) * vec3(2.539223, 1.207325, 1.400697);
    outCol += (rgb_p) * vec3(-9.477201, -5.706123, -7.924431);
    outCol += (rr*rr) * vec3(0.227090, 1.076939, 0.845224);
    outCol += (gg*gg) * vec3(0.407912, -1.097741, -0.434356);
    outCol += (bb*bb) * vec3(3.261456, 2.430522, -0.295413);
    outCol += (rrr*g) * vec3(-0.957284, 1.250664, -0.510902);
    outCol += (rrr*b) * vec3(-2.457334, 0.407421, -1.760870);
    outCol += (ggg*r) * vec3(1.197093, 0.346547, 0.226519);
    outCol += (ggg*b) * vec3(-3.785605, -1.529771, 0.481511);
    outCol += (bbb*r) * vec3(-1.142072, 0.677866, -0.615478);
    outCol += (bbb*g) * vec3(-2.606488, -0.520381, -0.504420);
    outCol += (rr*gg) * vec3(2.306712, 1.836107, 0.502025);
    outCol += (rr*bb) * vec3(2.438157, -1.268240, -0.355727);
    outCol += (gg*bb) * vec3(4.639595, 0.365129, -1.490437);
    outCol += (rr*gb) * vec3(2.379468, 2.298384, 2.700916);
    outCol += (gg*rb) * vec3(-1.010133, 0.370470, 2.676868);
    outCol += (bb*rg) * vec3(1.377538, -0.720146, 0.549225);
    outCol += (mx) * vec3(-0.228456, -0.442957, -0.100173);
    outCol += (mn) * vec3(-0.434374, -0.613678, -0.006723);
    outCol += (md) * vec3(0.055496, 0.199435, 0.257346);
    outCol += (ch) * vec3(0.011692, -0.168933, 0.057188);
    outCol += (ch*r) * vec3(-3.939781, -1.751268, -1.068379);
    outCol += (ch*g) * vec3(-3.891159, -1.668684, -1.385016);
    outCol += (ch*b) * vec3(-1.479141, -1.645689, -1.862081);
    outCol += (ch*mx) * vec3(2.701729, 1.598912, 1.212214);
    outCol += (ch*mn) * vec3(2.547980, 1.567623, 1.526178);
    outCol += (mx*mx) * vec3(1.221580, 1.217909, 0.376379);
    outCol += (mn*mn) * vec3(-3.167444, -1.063022, -1.253804);
    outCol += (ch*ch) * vec3(-0.152901, -0.327735, 0.202021);
    outCol += msEvalTetra9(x);
    return clamp(outCol, 0.0, 1.0);
}
