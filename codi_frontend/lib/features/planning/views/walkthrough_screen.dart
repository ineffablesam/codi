/// Walkthrough screen for showing completed implementation summary
library;

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';

/// Celebratory screen showing walkthrough of completed implementation
class WalkthroughScreen extends StatefulWidget {
  const WalkthroughScreen({super.key});

  @override
  State<WalkthroughScreen> createState() => _WalkthroughScreenState();
}

class _WalkthroughScreenState extends State<WalkthroughScreen> {
  late ConfettiController _confettiController;

  @override
  void initState() {
    super.initState();
    _confettiController = ConfettiController(duration: const Duration(seconds: 3));

    // Trigger confetti after 500ms
    Future.delayed(const Duration(milliseconds: 500), () {
      if (mounted) {
        _confettiController.play();
      }
    });
  }

  @override
  void dispose() {
    _confettiController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final args = Get.arguments as Map<String, dynamic>?;
    final walkthroughContent = args?['content'] as String? ?? '';

    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      body: Stack(
        children: [
          Column(
            children: [
              _buildHeader(),
              Expanded(
                child: _buildContent(walkthroughContent),
              ),
              _buildFooter(),
            ],
          ),
          Align(
            alignment: Alignment.topCenter,
            child: ConfettiWidget(
              confettiController: _confettiController,
              blastDirectionality: BlastDirectionality.explosive,
              particleDrag: 0.05,
              emissionFrequency: 0.05,
              numberOfParticles: 30,
              gravity: 0.2,
              shouldLoop: false,
              colors: const [
                Color(0xFF10B981),
                Color(0xFF3B82F6),
                Color(0xFF8B5CF6),
                Color(0xFFF59E0B),
                Color(0xFFEF4444),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: EdgeInsets.only(
        top: MediaQuery.of(context).padding.top + 16,
        left: 16,
        right: 16,
        bottom: 24,
      ),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF10B981),
            Color(0xFF059669),
          ],
        ),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white),
                onPressed: () => Get.back(),
              ),
              IconButton(
                icon: const Icon(Icons.share, color: Colors.white),
                onPressed: _handleShare,
              ),
            ],
          ),
          const SizedBox(height: 24),
          const Icon(
            Icons.celebration,
            size: 64,
            color: Colors.white,
          ),
          const SizedBox(height: 16),
          Text(
            '🎉 Implementation Complete!',
            style: GoogleFonts.inter(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            "Here's everything that was built",
            style: GoogleFonts.inter(
              fontSize: 15,
              color: Colors.white.withOpacity(0.9),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildContent(String markdown) {
    return Container(
      color: Colors.white,
      child: Markdown(
        data: markdown,
        selectable: true,
        styleSheet: MarkdownStyleSheet(
          h1: GoogleFonts.inter(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: Colors.black87,
          ),
          h2: GoogleFonts.inter(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: Colors.black87,
          ),
          h3: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: Colors.black87,
          ),
          p: GoogleFonts.inter(
            fontSize: 14,
            color: Colors.black87,
            height: 1.7,
          ),
          listBullet: GoogleFonts.inter(
            fontSize: 14,
            color: AppColors.success,
          ),
          code: GoogleFonts.jetBrainsMono(
            fontSize: 13,
            backgroundColor: const Color(0xFFF3F4F6),
          ),
          codeblockDecoration: BoxDecoration(
            color: const Color(0xFFF3F4F6),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[300]!),
          ),
          blockquote: GoogleFonts.inter(
            fontSize: 14,
            color: Colors.grey[700],
          ),
          blockquoteDecoration: BoxDecoration(
            color: const Color(0xFFDCFCE7).withOpacity(0.5),
            border: const Border(
              left: BorderSide(color: Color(0xFF10B981), width: 4),
            ),
          ),
        ),
        padding: const EdgeInsets.all(16),
      ),
    );
  }

  Widget _buildFooter() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: ElevatedButton(
          onPressed: () => Get.back(),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.success,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: Text(
            'Back to Project',
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }

  void _handleShare() {
    Get.snackbar(
      'Share',
      'Walkthrough sharing coming soon',
      snackPosition: SnackPosition.BOTTOM,
    );
  }
}
