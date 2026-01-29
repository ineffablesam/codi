import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';

import '../controllers/environment_controller.dart';
import '../models/environment_variable.dart';

class EnvironmentManagerScreen extends GetView<EnvironmentController> {
  const EnvironmentManagerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Environment Manager'),
        actions: [
          // Context filter
          PopupMenuButton<String?>(
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filter by context',
            onSelected: controller.setContext,
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: null,
                child: Text('All contexts'),
              ),
              const PopupMenuItem(
                value: 'docker-compose',
                child: Text('Docker Compose'),
              ),
              const PopupMenuItem(
                value: 'server-config',
                child: Text('Server Config'),
              ),
              const PopupMenuItem(
                value: 'flutter-build',
                child: Text('Flutter Build'),
              ),
              const PopupMenuItem(
                value: 'general',
                child: Text('General'),
              ),
            ],
          ),
          // Sync button
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: 'Sync to .env file',
            onPressed: controller.syncToFile,
          ),
          // Add button
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add variable',
            onPressed: () => _showAddEditDialog(context, null),
          ),
        ],
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }

        if (controller.error.value != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                Text('Error: ${controller.error.value}'),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: controller.loadVariables,
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (controller.variables.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.inbox, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                Text(
                  controller.selectedContext.value == null
                      ? 'No environment variables'
                      : 'No variables in ${controller.selectedContext.value} context',
                  style:
                      Get.textTheme.titleMedium?.copyWith(color: Colors.grey),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: () => _showAddEditDialog(context, null),
                  icon: const Icon(Icons.add),
                  label: const Text('Add Variable'),
                ),
              ],
            ),
          );
        }

        return MediaQuery.removePadding(
          context: context,
          removeTop: true,
          child: ListView.builder(
            itemCount: controller.variables.length,
            shrinkWrap: true,
            itemBuilder: (context, index) {
              final variable = controller.variables[index];
              return _VariableCard(
                variable: variable,
                onEdit: () => _showAddEditDialog(context, variable),
                onDelete: () =>
                    controller.deleteVariable(variable.id, variable.key),
              );
            },
          ),
        );
      }),
    );
  }

  void _showAddEditDialog(BuildContext context, EnvironmentVariable? existing) {
    Get.dialog(
      _AddEditVariableDialog(
        existing: existing,
        onSave: (variable) {
          if (existing == null) {
            controller.createVariable(variable);
          } else {
            controller.updateVariable(
              existing.id,
              EnvironmentVariableUpdate(
                value: variable.value,
                context: variable.context,
                isSecret: variable.isSecret,
                description: variable.description,
              ),
            );
          }
        },
      ),
    );
  }
}

class _VariableCard extends StatelessWidget {
  final EnvironmentVariable variable;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _VariableCard({
    required this.variable,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final showValue = false.obs;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row with key, badges, and actions
            Row(
              children: [
                Expanded(
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      Text(
                        variable.key,
                        style: Get.textTheme.titleMedium?.copyWith(
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (variable.isSecret)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.orange.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'SECRET',
                            style: TextStyle(fontSize: 10),
                          ),
                        ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: _getContextColor(variable.context),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          variable.context,
                          style: const TextStyle(fontSize: 10),
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.edit),
                  onPressed: onEdit,
                  tooltip: 'Edit',
                ),
                IconButton(
                  icon: const Icon(Icons.delete),
                  color: Colors.red,
                  onPressed: onDelete,
                  tooltip: 'Delete',
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Value row
            Row(
              children: [
                Expanded(
                  child: variable.isSecret
                      ? Obx(() {
                          String displayValue = variable.value;
                          if (!showValue.value) {
                            displayValue = '•' * 12;
                          }
                          return Text(
                            displayValue,
                            style: Get.textTheme.bodyMedium?.copyWith(
                              fontFamily: 'monospace',
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          );
                        })
                      : Text(
                          variable.value,
                          style: Get.textTheme.bodyMedium?.copyWith(
                            fontFamily: 'monospace',
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                ),
                if (variable.isSecret)
                  IconButton(
                    icon: Obx(() => Icon(
                          showValue.value
                              ? Icons.visibility_off
                              : Icons.visibility,
                          size: 20,
                        )),
                    onPressed: () => showValue.value = !showValue.value,
                    tooltip: 'Toggle visibility',
                  ),
                IconButton(
                  icon: const Icon(Icons.copy, size: 20),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: variable.value));
                    Get.snackbar(
                      'Copied',
                      'Value copied to clipboard',
                      snackPosition: SnackPosition.BOTTOM,
                      duration: const Duration(seconds: 2),
                    );
                  },
                  tooltip: 'Copy value',
                ),
              ],
            ),
            if (variable.description != null) ...[
              const SizedBox(height: 8),
              Text(
                variable.description!,
                style: Get.textTheme.bodySmall?.copyWith(color: Colors.grey),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _getContextColor(String context) {
    switch (context) {
      case 'docker-compose':
        return Colors.blue.withOpacity(0.2);
      case 'server-config':
        return Colors.green.withOpacity(0.2);
      case 'flutter-build':
        return Colors.purple.withOpacity(0.2);
      default:
        return Colors.grey.withOpacity(0.2);
    }
  }
}

class _AddEditVariableDialog extends StatefulWidget {
  final EnvironmentVariable? existing;
  final void Function(EnvironmentVariableCreate) onSave;

  const _AddEditVariableDialog({
    this.existing,
    required this.onSave,
  });

  @override
  State<_AddEditVariableDialog> createState() => _AddEditVariableDialogState();
}

class _AddEditVariableDialogState extends State<_AddEditVariableDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _keyController;
  late final TextEditingController _valueController;
  late final TextEditingController _descriptionController;
  late String _context;
  late bool _isSecret;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _keyController = TextEditingController(text: existing?.key ?? '');
    _valueController = TextEditingController(text: existing?.value ?? '');
    _descriptionController =
        TextEditingController(text: existing?.description ?? '');
    _context = existing?.context ?? 'general';
    _isSecret = existing?.isSecret ?? false;
  }

  @override
  void dispose() {
    _keyController.dispose();
    _valueController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;

    widget.onSave(
      EnvironmentVariableCreate(
        key: _keyController.text.trim(),
        value: _valueController.text,
        context: _context,
        isSecret: _isSecret,
        description: _descriptionController.text.isEmpty
            ? null
            : _descriptionController.text.trim(),
      ),
    );

    Get.back();
  }

  @override
  Widget build(BuildContext context) {
    final isEdit = widget.existing != null;

    return AlertDialog(
      title: Text(isEdit ? 'Edit Variable' : 'Add Variable'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _keyController,
                decoration: const InputDecoration(
                  labelText: 'Key',
                  hintText: 'VARIABLE_NAME',
                  helperText: 'Uppercase letters, numbers, and underscores',
                ),
                enabled: !isEdit,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Key is required';
                  }
                  if (!RegExp(r'^[A-Z_][A-Z0-9_]*$').hasMatch(value)) {
                    return 'Must be UPPERCASE_WITH_UNDERSCORES';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _valueController,
                decoration: const InputDecoration(labelText: 'Value'),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Value is required';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _context,
                decoration: const InputDecoration(labelText: 'Context'),
                items: const [
                  DropdownMenuItem(value: 'general', child: Text('General')),
                  DropdownMenuItem(
                      value: 'docker-compose', child: Text('Docker Compose')),
                  DropdownMenuItem(
                      value: 'server-config', child: Text('Server Config')),
                  DropdownMenuItem(
                      value: 'flutter-build', child: Text('Flutter Build')),
                ],
                onChanged: (value) {
                  if (value != null) setState(() => _context = value);
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _descriptionController,
                decoration:
                    const InputDecoration(labelText: 'Description (optional)'),
                maxLines: 2,
              ),
              const SizedBox(height: 16),
              SwitchListTile(
                title: const Text('Secret'),
                subtitle: const Text('Encrypt this value'),
                value: _isSecret,
                onChanged: (value) => setState(() => _isSecret = value),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _save,
          child: Text(isEdit ? 'Save' : 'Add'),
        ),
      ],
    );
  }
}
