import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    title: "Language & appearance"
    description: "Choose the default content language for new projects. The application UI is currently English; this does not claim full UI translation."
    Text { text: "Content language"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
    GridLayout {
        Layout.fillWidth: true; columns: width < 700 ? 2 : 4; columnSpacing: Theme.spacing.sm; rowSpacing: Theme.spacing.sm
        Repeater {
            model: Onboarding.languages
            delegate: RadioCard {
                required property var modelData
                Layout.fillWidth: true; implicitHeight: 72
                title: String(modelData.nativeName || modelData.displayName || modelData.code)
                description: String(modelData.displayName || modelData.code) + (modelData.details && modelData.details.overall ? " · " + String(modelData.details.overall).replaceAll("_"," ") : "")
                value: String(modelData.code || "en")
                selected: Onboarding.defaultContentLanguage === value
                onChosen: Onboarding.setContentLanguage(value)
            }
        }
    }
    Text { text: "Theme"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
    RowLayout {
        Layout.fillWidth: true
        RadioCard { Layout.fillWidth: true; title: "System"; description: "Follow Windows"; value: "system"; selected: Onboarding.theme === value; onChosen: Onboarding.setTheme(value) }
        RadioCard { Layout.fillWidth: true; title: "Light"; description: "Bright, calm workspace"; value: "light"; selected: Onboarding.theme === value; onChosen: Onboarding.setTheme(value) }
        RadioCard { Layout.fillWidth: true; title: "Dark"; description: "Comfortable low-light UI"; value: "dark"; selected: Onboarding.theme === value; onChosen: Onboarding.setTheme(value) }
    }
    RowLayout {
        Layout.fillWidth: true
        AppSwitch { text: "Reduce Motion"; checked: Onboarding.reduceMotionMode === "on"; onToggled: Onboarding.setReduceMotion(checked) }
        AppSwitch { text: "Larger Text"; checked: Onboarding.interfaceTextSize === "large"; onToggled: Onboarding.setLargeText(checked) }
        Item { Layout.fillWidth: true }
    }
    Text { Layout.fillWidth: true; text: "Test text: សួស្តី អ្នកអាចចាប់ផ្ដើមបង្កើតវីដេអូបាន។ · สวัสดี คุณสามารถเริ่มสร้างวิดีโอได้เลย · Xin chào, bạn có thể bắt đầu tạo video."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; lineHeight: 1.3 }
}
