import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"

ColumnLayout {
    id: root
    property string currentCode: "en"
    property string engineId: ""
    property string capability: "all" // all | tts
    property string sourceCode: ""
    signal codeSelected(string code)
    spacing: 4
    AppTextField {
        id: search
        Layout.fillWidth: true
        placeholderText: "Search language"
        onTextChanged: combo.model = LanguageCatalog.search(text)
    }
    AppComboBox {
        id: combo
        Layout.fillWidth: true
        model: LanguageCatalog.languages
        textRole: "nativeName"
        Component.onCompleted: selectCode(root.currentCode)
        onActivated: {
            if (currentIndex < 0 || !model || currentIndex >= model.length) return
            root.currentCode = model[currentIndex].code
            root.codeSelected(root.currentCode)
        }
        function selectCode(code) {
            for (var i=0; model && i<model.length; ++i) if (model[i].code === code) { currentIndex=i; return }
        }
        contentItem: Text {
            text: combo.currentIndex >= 0 && combo.model && combo.currentIndex < combo.model.length ?
                  combo.model[combo.currentIndex].nativeName + " · " + combo.model[combo.currentIndex].displayName : "Choose language"
            color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
    }
    Text {
        Layout.fillWidth: true
        visible: combo.currentIndex >= 0 && combo.model && combo.currentIndex < combo.model.length
        text: {
            if (!visible) return ""
            var row=combo.model[combo.currentIndex]
            return "STT: "+row.sttSupport.replaceAll("_"," ")+" · TTS: "+row.ttsSupport.replaceAll("_"," ")+" · Translation: "+row.translationSupport.replaceAll("_"," ")
        }
        color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; wrapMode: Text.WordWrap
    }
}
