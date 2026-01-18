import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:screen_corner_radius/screen_corner_radius.dart';

class UIController extends GetxController {
  /// Hardware corner radii
  final RxDouble topLeft = 24.0.obs;
  final RxDouble topRight = 24.0.obs;
  final RxDouble bottomLeft = 24.0.obs;
  final RxDouble bottomRight = 24.0.obs;

  @override
  void onInit() {
    super.onInit();
    _initCornerRadius();
  }

  Future<void> _initCornerRadius() async {
    try {
      final ScreenRadius? radius = await ScreenCornerRadius.get();

      topLeft.value = _parse(radius?.topLeft);
      topRight.value = _parse(radius?.topRight);
      bottomLeft.value = _parse(radius?.bottomLeft);
      bottomRight.value = _parse(radius?.bottomRight);
    } catch (_) {
      _fallback();
    }
  }

  double _parse(Object? value) {
    if (value is double) return value;
    if (value is int) return value.toDouble();
    return 24.0;
  }

  void _fallback() {
    topLeft.value = 24.0;
    topRight.value = 24.0;
    bottomLeft.value = 24.0;
    bottomRight.value = 24.0;
  }

  // --------------------------------------------------
  // 🔥 Radius helpers (USE THESE EVERYWHERE)
  // --------------------------------------------------

  /// EXACT hardware radius (all corners)
  BorderRadius all({double factor = 1.0}) {
    return BorderRadius.only(
      topLeft: Radius.circular(topLeft.value * factor),
      topRight: Radius.circular(topRight.value * factor),
      bottomLeft: Radius.circular(bottomLeft.value * factor),
      bottomRight: Radius.circular(bottomRight.value * factor),
    );
  }

  /// Top corners only
  BorderRadius top({double factor = 1.0}) {
    return BorderRadius.only(
      topLeft: Radius.circular(topLeft.value * factor),
      topRight: Radius.circular(topRight.value * factor),
    );
  }

  /// Bottom corners only
  BorderRadius bottom({double factor = 1.0}) {
    return BorderRadius.only(
      bottomLeft: Radius.circular(bottomLeft.value * factor),
      bottomRight: Radius.circular(bottomRight.value * factor),
    );
  }

  /// Bottom sheet standard (top only)
  BorderRadius sheet({double factor = 1.0}) {
    return top(factor: factor);
  }

  /// Card-style (slightly reduced)
  BorderRadius card({double factor = 0.75}) {
    return all(factor: factor);
  }

  /// Dialog radius
  BorderRadius dialog({double factor = 0.9}) {
    return all(factor: factor);
  }

  /// Fullscreen modal (top hardware radius)
  BorderRadius modal({double factor = 1.0}) {
    return BorderRadius.vertical(
      top: Radius.circular(
        ((topLeft.value + topRight.value) / 2) * factor,
      ),
    );
  }
}
