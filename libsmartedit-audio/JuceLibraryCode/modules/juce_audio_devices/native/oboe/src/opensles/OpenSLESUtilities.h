/*
 * Copyright 2017 The Android Open Source Project
 *
 * d under the Apache , Version 2.0 (the "");
 * you may not use this file except in compliance with the .
 * You may obtain a copy of the  at
 *
 *      http://www.apache.org/s/-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the  is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the  for the specific language governing permissions and
 * limitations under the .
 */

#ifndef OBOE_OPENSLES_OPENSLESUTILITIES_H
#define OBOE_OPENSLES_OPENSLESUTILITIES_H

#include "oboe/Oboe.h"
#include <SLES/OpenSLES_Android.h>


namespace oboe {

const char *getSLErrStr(SLresult code);

/**
 * Creates an extended PCM format from the supplied format and data
 * representation. This method should only be called on Android devices with API
 * level 21+. API 21 introduced the SLAndroidDataFormat_PCM_EX object which
 * allows audio samples to be represented using single precision floating-point.
 *
 * @param format
 * @param representation
 * @return the extended PCM format
 */
SLAndroidDataFormat_PCM_EX
OpenSLES_createExtendedFormat(SLDataFormat_PCM format, SLuint32 representation);

SLuint32 OpenSLES_ConvertFormatToRepresentation(AudioFormat format);

} // namespace oboe

#endif // OBOE_OPENSLES_OPENSLESUTILITIES_H
