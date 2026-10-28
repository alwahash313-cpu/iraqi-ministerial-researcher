
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MinisterialApp());
}

const Color pageColor = Color(0xFF101318);
const Color cardColor = Color(0xFF1D232C);
const Color goldColor = Color(0xFFC8A875);
const Color mutedColor = Color(0xFFAEB6C1);

const String reportUrl =
    'https://raw.githubusercontent.com/alwahash313-cpu/iraqi-ministerial-researcher/main/reports/latest.json';

class MinisterialApp extends StatelessWidget {
  const MinisterialApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'الباحث الوزاري العراقي',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: pageColor,
        colorScheme: ColorScheme.fromSeed(
          seedColor: goldColor,
          brightness: Brightness.dark,
        ),
        fontFamily: 'Arial',
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool loading = false;
  String? error;
  Map<String, dynamic> results = {};
  String selectedSubject = 'الكل';
  String updatedAt = '';

  final List<String> subjects = const [
    'الكل',
    'اللغة العربية',
    'اللغة الإنجليزية',
    'الرياضيات',
    'الكيمياء',
    'الفيزياء',
    'الأحياء',
    'الاجتماعيات',
    'التربية الإسلامية',
  ];

  @override
  void initState() {
    super.initState();
    loadResults();
  }

  Future<void> loadResults() async {
    if (loading) return;

    setState(() {
      loading = true;
      error = null;
    });

    try {
      final uri = Uri.parse(reportUrl).replace(
        queryParameters: {
          'refresh': DateTime.now().millisecondsSinceEpoch.toString(),
        },
      );

      final response = await http.get(
        uri,
        headers: const {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
        },
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode != 200) {
        throw Exception(
          'خادم GitHub رجّع رمز HTTP ${response.statusCode}',
        );
      }

      final decoded = jsonDecode(
        utf8.decode(response.bodyBytes),
      );

      if (decoded is! Map) {
        throw const FormatException(
          'التقرير ليس بصيغة JSON المتوقعة',
        );
      }

      final parsed = Map<String, dynamic>.from(decoded);

      if (parsed['results'] is! List) {
        throw const FormatException(
          'ملف التقرير لا يحتوي على قائمة results صحيحة',
        );
      }

      if (!mounted) return;

      setState(() {
        results = parsed;
        updatedAt = parsed['updated_at']?.toString() ?? '';
        error = null;
      });
    } on SocketException catch (e) {
      _setError('تعذر الاتصال بالشبكة: ${e.message}');
    } on TimeoutException {
      _setError(
        'انتهت مهلة الاتصال. جرّب شبكة إنترنت أخرى ثم أعد المحاولة.',
      );
    } on FormatException catch (e) {
      _setError('مشكلة بصيغة التقرير: ${e.message}');
    } catch (e) {
      _setError('تفاصيل الخطأ: $e');
    } finally {
      if (mounted) {
        setState(() {
          loading = false;
        });
      }
    }
  }

  void _setError(String message) {
    if (!mounted) return;
    setState(() {
      error = message;
    });
  }

  List<Map<String, dynamic>> get visibleResults {
    final raw = results['results'];
    if (raw is! List) return [];

    return raw
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .where((item) {
          if (selectedSubject == 'الكل') return true;
          return item['subject']?.toString() == selectedSubject;
        })
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: pageColor,
          title: const Text(
            'الباحث الوزاري',
            style: TextStyle(
              color: goldColor,
              fontWeight: FontWeight.bold,
            ),
          ),
          actions: [
            IconButton(
              tooltip: 'تحديث النتائج',
              onPressed: loading ? null : loadResults,
              icon: const Icon(
                Icons.refresh,
                color: goldColor,
              ),
            ),
          ],
        ),
        body: RefreshIndicator(
          color: goldColor,
          onRefresh: loadResults,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [
                      Color(0xFF30302B),
                      Color(0xFF1D232C),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: goldColor.withValues(alpha: 0.4),
                  ),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.school,
                      color: goldColor,
                      size: 36,
                    ),
                    SizedBox(height: 12),
                    Text(
                      'دليلك الدراسي الذكي',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 23,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'نتائج البحث عن ملخصات ومرشحات '
                      'الثالث المتوسط العراقي من المصادر العامة.',
                      style: TextStyle(
                        color: mutedColor,
                        height: 1.7,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 22),
              const Text(
                'المواد الدراسية',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 19,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: subjects.map((subject) {
                  final selected = selectedSubject == subject;

                  return ChoiceChip(
                    label: Text(subject),
                    selected: selected,
                    selectedColor: goldColor,
                    backgroundColor: cardColor,
                    labelStyle: TextStyle(
                      color: selected ? pageColor : Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                    onSelected: (_) {
                      setState(() {
                        selectedSubject = subject;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'أحدث النتائج',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 19,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  if (updatedAt.isNotEmpty)
                    Flexible(
                      child: Text(
                        updatedAt,
                        textAlign: TextAlign.left,
                        style: const TextStyle(
                          color: mutedColor,
                          fontSize: 10,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              if (loading && results.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(30),
                  child: Center(
                    child: CircularProgressIndicator(
                      color: goldColor,
                    ),
                  ),
                )
              else if (error != null && results.isEmpty)
                _messageCard(
                  error!,
                  icon: Icons.wifi_off,
                  action: true,
                )
              else if (visibleResults.isEmpty && !loading)
                _messageCard(
                  error ??
                      'ماكو نتائج لهذه المادة حالياً. '
                          'جرّب التحديث لاحقاً.',
                  icon: Icons.search,
                  action: error != null,
                )
              else ...[
                if (error != null)
                  _messageCard(
                    'تعذر تحديث النتائج الجديدة:\n$error',
                    icon: Icons.warning_amber,
                    action: true,
                  ),
                if (loading)
                  const LinearProgressIndicator(
                    color: goldColor,
                    backgroundColor: cardColor,
                  ),
                ...visibleResults.map(_resultCard),
              ],
              const SizedBox(height: 20),
              const Text(
                'يتم تحديث التقرير بواسطة الباحث على GitHub. '
                'قد تختلف النتائج حسب المصادر المتاحة.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: mutedColor,
                  fontSize: 12,
                  height: 1.7,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _messageCard(
    String message, {
    required IconData icon,
    bool action = false,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Icon(icon, color: goldColor, size: 30),
          const SizedBox(height: 10),
          SelectableText(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: mutedColor,
              height: 1.7,
            ),
          ),
          if (action) ...[
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: loading ? null : loadResults,
              child: const Text('إعادة المحاولة'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _resultCard(Map<String, dynamic> item) {
    final title = item['title']?.toString() ?? 'نتيجة بدون عنوان';
    final subject = item['subject']?.toString() ?? 'غير محدد';
    final source = item['source']?.toString() ?? 'مصدر عام';
    final url = item['url']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.article_outlined,
                color: goldColor,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  subject,
                  style: const TextStyle(
                    color: goldColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'المصدر: $source',
            style: const TextStyle(
              color: mutedColor,
              fontSize: 12,
            ),
          ),
          if (url.startsWith('https://'))
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text(
                        'فتح الروابط يحتاج إضافة مكتبة مخصصة، '
                        'وسنضيفها بالخطوة التالية.',
                      ),
                    ),
                  );
                },
                icon: const Icon(
                  Icons.link,
                  color: goldColor,
                ),
                label: const Text(
                  'رابط المصدر',
                  style: TextStyle(color: goldColor),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
