> The strategies need to be carefully reviewed and tested.
> If a strategy is logically similar to another one, they should be merged.
>
> In the end, I want to have a **final list of strategies** that are:
>
> * Unique
> * Ready for backtesting
> * And even ready for live trading on a **BingX test account**
>
> So please carefully review and analyze **all the contents of `infrastructure/strategies`**.
> Finalize the strategies so we can move on to the next step.




### **1. Architectural Compliance**

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.

### **2. Integration & Functional Testing**
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **3. Quality & Validation**
* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.


