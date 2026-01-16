---
description: "Serverpod endpoint template"
---
import 'package:serverpod/serverpod.dart';
import '../generated/protocol.dart';

class {{endpoint_name}}Endpoint extends Endpoint {
  Future<{{return_type}}> {{method_name}}(Session session{{#if has_params}}, {{params}}{{/if}}) async {
    // TODO: Implement endpoint logic
    {{method_body}}
  }
}
