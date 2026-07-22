from __future__ import annotations


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
