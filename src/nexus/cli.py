import sys, json
import click
from pathlib import Path
from nexus.core.config import load_config
from nexus.core.audit import audit


def format_simple_output(result: dict) -> str:
    """Format detection results in a simple, clean way - just the essentials."""
    lines = []
    
    candidates = result['candidates']
    
    if not candidates:
        lines.append("❌ No matches found")
        return "\n".join(lines)
    
    # Just show top result with high confidence
    top = candidates[0]
    score = top['score']
    name = top['name'].replace('_', ' ').title()
    
    if score >= 0.85:
        lines.append(f"✓ Detected: {name} ({score:.0%} confidence)")
    elif score >= 0.70:
        lines.append(f"→ Likely: {name} ({score:.0%} confidence)")
    else:
        lines.append(f"? Possibly: {name} ({score:.0%} confidence)")
    
    # Show runner-ups if they're close
    if len(candidates) > 1:
        alternates = []
        for candidate in candidates[1:4]:  # Show up to 3 alternates
            if candidate['score'] > 0.65:  # Only show strong alternates
                alternates.append(candidate['name'].replace('_', ' ').title())
        
        if alternates:
            lines.append(f"   Also consider: {', '.join(alternates)}")
    
    return "\n".join(lines)


def format_detailed_output(result: dict) -> str:
    """Format detection results with full details and analysis."""
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append("🔍 CRYPTOGRAPHIC DETECTION RESULTS")
    lines.append("=" * 70)
    
    # Input info
    lines.append(f"\n📊 Input Analysis:")
    lines.append(f"   Length: {result['input_length']} characters")
    
    # Metrics
    metrics = result['metrics']
    lines.append(f"\n📈 Metrics:")
    lines.append(f"   Entropy:              {metrics['entropy']:.4f} bits/byte")
    lines.append(f"   Printable Ratio:      {metrics['printable_ratio']:.2%}")
    lines.append(f"   Index of Coincidence: {metrics['index_of_coincidence']:.4f}")
    
    # Interpretation hints
    ic = metrics['index_of_coincidence']
    ent = metrics['entropy']
    lines.append(f"\n💡 Statistical Interpretation:")
    
    # Entropy interpretation
    if ent > 7.5:
        lines.append(f"   ⚡ High entropy ({ent:.2f}) suggests modern encryption or compression")
        lines.append(f"      → Data is highly random, likely AES/ChaCha20 or compressed")
    elif ent > 6.0:
        lines.append(f"   📝 Medium entropy ({ent:.2f}) suggests encoding or weak encryption")
        lines.append(f"      → Could be Base64/hex encoded data or classical cipher")
    else:
        lines.append(f"   📄 Low entropy ({ent:.2f}) suggests plaintext or simple cipher")
        lines.append(f"      → Natural language or very simple substitution")
    
    # IC interpretation with more detail
    lines.append("")
    if ic > 0.060:
        lines.append(f"   🔤 High IC ({ic:.4f}) suggests monoalphabetic or transposition")
        lines.append(f"      → Letter frequencies preserved (Caesar, Atbash, substitution)")
        lines.append(f"      → IC close to English (0.067) - same letters, different order")
    elif ic > 0.045:
        lines.append(f"   🔄 Medium IC ({ic:.4f}) suggests polyalphabetic cipher")
        lines.append(f"      → Flattened letter frequencies (Vigenère, Beaufort, etc.)")
        lines.append(f"      → Multiple alphabets used")
    elif ic > 0.030:
        lines.append(f"   🎲 Low IC ({ic:.4f}) suggests random or strong encryption")
        lines.append(f"      → Very uniform distribution (modern cipher or random data)")
    
    # Candidates with full details
    candidates = result['candidates']
    if not candidates:
        lines.append(f"\n❌ No strong matches found")
        lines.append(f"   The input doesn't match any known patterns")
    else:
        lines.append(f"\n🎯 Detection Results ({len(candidates)} candidates):")
        lines.append("")
        
        for i, candidate in enumerate(candidates, 1):
            score = candidate['score']
            name = candidate['name']
            category = candidate.get('category', 'unknown')
            
            # Score bar (longer for detailed view)
            bar_length = int(score * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            
            # Confidence emoji
            if score >= 0.85:
                confidence = "🟢 Very High"
                reliability = "Strongly recommended"
            elif score >= 0.70:
                confidence = "🟡 High"
                reliability = "Recommended"
            elif score >= 0.55:
                confidence = "🟠 Medium"
                reliability = "Consider as possibility"
            else:
                confidence = "🔴 Low"
                reliability = "Weak match"
            
            # Category emoji and description
            category_info = {
                'encoder': ('📦', 'Encoder', 'Text representation or encoding scheme'),
                'armor': ('🛡️', 'Armor', 'ASCII armored binary data'),
                'classical_cipher': ('📜', 'Classical Cipher', 'Historical encryption method'),
                'modern_cipher': ('🔐', 'Modern Cipher', 'Strong cryptographic algorithm'),
                'container': ('📁', 'Container', 'File format or compression'),
                'unknown': ('❓', 'Unknown', 'Unclassified')
            }
            emoji, cat_name, cat_desc = category_info.get(category, ('❓', 'Unknown', 'Unclassified'))
            
            lines.append(f"   {i}. {name.replace('_', ' ').title()}")
            lines.append(f"      {bar} {score:.1%}")
            lines.append(f"      Confidence: {confidence} ({reliability})")
            lines.append(f"      Category:   {emoji} {cat_name} - {cat_desc}")
            
            # Additional parameters if present
            if 'params' in candidate:
                params = candidate['params']
                if params:
                    lines.append(f"      Parameters:")
                    for key, value in params.items():
                        if isinstance(value, float):
                            lines.append(f"         • {key}: {value:.4f}")
                        elif isinstance(value, list):
                            lines.append(f"         • {key}: {', '.join(str(v) for v in value[:5])}")
                            if len(value) > 5:
                                lines.append(f"           ... and {len(value) - 5} more")
                        else:
                            lines.append(f"         • {key}: {value}")
            
            if i < len(candidates):
                lines.append("")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


def format_compact_output(result: dict) -> str:
    """Format detection results in a compact table format."""
    lines = []
    
    lines.append(f"Input: {result['input_length']} chars | "
                f"Entropy: {result['metrics']['entropy']:.2f} | "
                f"IC: {result['metrics']['index_of_coincidence']:.4f}")
    lines.append("")
    lines.append(f"{'#':<4} {'Name':<32} {'Score':<8} {'Category':<20}")
    lines.append("-" * 70)
    
    for i, candidate in enumerate(result['candidates'], 1):
        name = candidate['name'].replace('_', ' ').title()
        score = f"{candidate['score']:.1%}"
        category = candidate.get('category', 'unknown').replace('_', ' ').title()
        lines.append(f"{i:<4} {name:<32} {score:<8} {category:<20}")
    
    return "\n".join(lines)


@click.group()
@click.option("--config", default="~/.nexus/config.toml", help="Path to config TOML")
@click.pass_context
def cli(ctx, config):
    ctx.obj = load_config(config)


# -------- CRYPT --------
@cli.group()
def crypt():
    """Cryptography helpers"""
    pass


@crypt.command("detect")
@click.option("-i", "--input", "inline", type=str, required=True,
              help="Inline payload only (no files).")
@click.option("-f", "--format", type=click.Choice(['simple', 'detailed', 'compact', 'json'], case_sensitive=False),
              default='simple', help="Output format (default: simple)")
@click.option("--top", type=int, default=10, help="Number of top candidates to show")
@click.pass_context
def crypt_detect(ctx, inline, format, top):
    """
    Detect cryptographic encodings, ciphers, and formats.
    
    Examples:
    
        # Simple one-line answer (default)
        nexus crypt detect -i "SGVsbG8gV29ybGQh"
        
        # Detailed analysis with full metrics
        nexus crypt detect -i "SGVsbG8gV29ybGQh" --format detailed
        
        # Compact table format
        nexus crypt detect -i "c2NyaWJibGU=" --format compact
        
        # Raw JSON for scripting
        nexus crypt detect -i "URYYB JBEYQ" --format json --top 5
    """
    from nexus.modules.cryptography.service import detect
    
    try:
        res = detect(inline)
        
        # Limit candidates to requested top N
        if res and 'candidates' in res and len(res['candidates']) > top:
            res['candidates'] = res['candidates'][:top]
        
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=bool(res), 
              notes=f"candidates={len(res.get('candidates', [])) if res else 0}")
        
        # Format output based on user preference
        if format == 'json':
            output = json.dumps(res, ensure_ascii=False, indent=2)
        elif format == 'compact':
            output = format_compact_output(res)
        elif format == 'detailed':
            output = format_detailed_output(res)
        else:  # simple
            output = format_simple_output(res)
        
        click.echo(output)
        sys.exit(0 if res else 3)
        
    except Exception as e:
        click.echo(f"❌ Error during detection: {str(e)}", err=True)
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=False, notes=f"error: {str(e)}")
        sys.exit(1)


# -------- OSINT --------
@cli.group()
def osint():
    """OSINT metadata"""
    pass


@osint.command("meta")
@click.option("-i", "--input", type=click.Path(exists=True), required=True)
@click.pass_context
def osint_meta(ctx, input):
    from nexus.modules.osint.service import extract_meta
    res = extract_meta(input)
    audit(ctx.obj, module="osint", action="meta", target=input, success_bool=bool(res))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res else 3)


# -------- LOG --------
@cli.group()
def log():
    """Log ingestion and analytics"""
    pass


@log.command("ingest")
@click.option("-i", "--input", type=click.Path(exists=True), required=True)
@click.pass_context
def log_ingest(ctx, input):
    from nexus.modules.log_analysis.service import ingest
    res = ingest(ctx.obj, Path(input))
    audit(ctx.obj, module="log", action="ingest", target=input, success_bool=bool(res),
          notes=f"table={res.get('table')} rows={res.get('rows', 0)}")
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("table") else 1)


@log.command("canned")
@click.argument("name")
@click.option("--params", default="{}")
@click.pass_context
def log_canned(ctx, name, params):
    from nexus.modules.log_analysis.service import run_canned
    res = run_canned(ctx.obj, name, json.loads(params))
    audit(ctx.obj, module="log", action=f"canned:{name}",
          target=res.get('table', ''), success_bool=bool(res.get('result')))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("result") is not None else 3)


# -------- ENUM --------
@cli.group()
def enum():
    """Enumeration helpers"""
    pass


@enum.command("code-id")
@click.option("-i", "--input", "inline", required=True, type=str,
              help="Inline code snippet only.")
@click.pass_context
def code_id(ctx, inline):
    from nexus.modules.enumeration.service import detect_language
    res = detect_language(inline)
    audit(ctx.obj, module="enum", action="code-id", target="[inline]", success_bool=bool(res))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("candidates") else 3)