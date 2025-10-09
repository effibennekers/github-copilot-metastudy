"""
Converter functies voor bestandsconversie en tarball-beheer.
"""

import subprocess
import os
import sys
import tarfile
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def tex_naar_md(input_file: str, paper_id: str, output_dir: Optional[str] = None) -> str:
    """
    Converteer een TeX bestand naar Markdown met pandoc.
    
    Args:
        input_file: Pad naar het input TeX bestand
        paper_id: ID van het paper voor de output filename
        output_dir: Directory voor output, standaard hetzelfde als input
        
    Returns:
        Pad naar het gegenereerde markdown bestand
        
    Raises:
        subprocess.CalledProcessError: Als pandoc conversie faalt
        FileNotFoundError: Als input bestand niet bestaat
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input bestand niet gevonden: {input_file}")
    
    if output_dir is None:
        output_dir = os.path.dirname(input_file)
    
    output_file = os.path.join(output_dir, f"{paper_id}.md")
    
    pandoc_options = ["--from", "latex", "--to", "markdown+tex_math_dollars"]
    command = ["pandoc", "-s", input_file, "-o", output_file] + pandoc_options
    
    try:
        logger.info(f"Converteer TeX naar MD: {input_file} -> {output_file}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"Pandoc output: {result.stdout}")
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc conversie gefaald: {e.stderr}")
        raise


def html_naar_md(input_file: str, paper_id: str, output_dir: Optional[str] = None) -> str:
    """
    Converteer een HTML bestand naar Markdown met pandoc.
    
    Args:
        input_file: Pad naar het input HTML bestand
        paper_id: ID van het paper voor de output filename
        output_dir: Directory voor output, standaard hetzelfde als input
        
    Returns:
        Pad naar het gegenereerde markdown bestand
        
    Raises:
        subprocess.CalledProcessError: Als pandoc conversie faalt
        FileNotFoundError: Als input bestand niet bestaat
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input bestand niet gevonden: {input_file}")
    
    if output_dir is None:
        output_dir = os.path.dirname(input_file)
    
    output_file = os.path.join(output_dir, f"{paper_id}.md")
    
    pandoc_options = ["--from", "html", "--to", "markdown"]
    command = ["pandoc", "-s", input_file, "-o", output_file] + pandoc_options
    
    try:
        logger.info(f"Converteer HTML naar MD: {input_file} -> {output_file}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"Pandoc output: {result.stdout}")
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc conversie gefaald: {e.stderr}")
        raise


def pak_tarball_uit(tarball_path: str, extract_to: Optional[str] = None) -> str:
    """
    Pak een tarball uit naar een directory.
    
    Args:
        tarball_path: Pad naar het tarball bestand
        extract_to: Directory om naar uit te pakken, standaard parent directory van tarball
        
    Returns:
        Pad naar de uitgepakte directory
        
    Raises:
        FileNotFoundError: Als tarball niet bestaat
        tarfile.TarError: Als er een probleem is met het uitpakken
    """
    if not os.path.exists(tarball_path):
        raise FileNotFoundError(f"Tarball niet gevonden: {tarball_path}")
    
    if extract_to is None:
        extract_to = os.path.dirname(tarball_path)
    
    # Maak extract directory als het niet bestaat
    os.makedirs(extract_to, exist_ok=True)
    
    try:
        logger.info(f"Pak tarball uit: {tarball_path} -> {extract_to}")
        
        with tarfile.open(tarball_path, 'r:*') as tar:
            # Krijg de root directory naam uit de tarball
            members = tar.getnames()
            if members:
                root_dir = members[0].split('/')[0]
                extract_path = os.path.join(extract_to, root_dir)
            else:
                extract_path = extract_to
            
            # Pak uit
            tar.extractall(path=extract_to)
            
            logger.info(f"Tarball uitgepakt naar: {extract_path}")
            return extract_path
            
    except tarfile.TarError as e:
        logger.error(f"Fout bij uitpakken tarball: {e}")
        raise


def verwijder_uitgepakte_tarball(extracted_path: str, force: bool = False) -> bool:
    """
    Verwijder een uitgepakte tarball directory.
    
    Args:
        extracted_path: Pad naar de uitgepakte directory
        force: Of directory geforceerd verwijderd moet worden (ook bij non-empty)
        
    Returns:
        True als succesvol verwijderd, False anders
        
    Raises:
        OSError: Als er een probleem is met het verwijderen
    """
    if not os.path.exists(extracted_path):
        logger.warning(f"Directory bestaat niet: {extracted_path}")
        return False
    
    if not os.path.isdir(extracted_path):
        logger.error(f"Pad is geen directory: {extracted_path}")
        return False
    
    try:
        logger.info(f"Verwijder uitgepakte directory: {extracted_path}")
        
        if force:
            shutil.rmtree(extracted_path)
        else:
            # Probeer eerst lege directory te verwijderen
            try:
                os.rmdir(extracted_path)
            except OSError:
                # Als niet leeg, verwijder alles
                shutil.rmtree(extracted_path)
        
        logger.info(f"Directory succesvol verwijderd: {extracted_path}")
        return True
        
    except OSError as e:
        logger.error(f"Fout bij verwijderen directory: {e}")
        raise
